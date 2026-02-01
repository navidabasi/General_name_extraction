"""
Worker thread for background processing to keep UI responsive.
"""

from PyQt6.QtCore import QThread, pyqtSignal
import pandas as pd
import logging

from data_loader import load_ventrata, load_monday, load_update_file, merge_data
from processor import NameExtractionProcessor
from main import save_results_to_excel, get_next_available_filename

logger = logging.getLogger(__name__)


class ExtractionWorker(QThread):
    """
    Background worker thread for name extraction processing.
    
    Signals:
        progress_updated: (step: str, state: str, details: str)
        warning_added: (warning: str)
        finished: (success: bool, message: str, output_file: str)
        error_occurred: (error_message: str)
    """
    
    progress_updated = pyqtSignal(str, str, str)  # step, state, details
    warning_added = pyqtSignal(str)  # warning message
    finished = pyqtSignal(bool, str, str)  # success, message, output_file
    error_occurred = pyqtSignal(str)  # error message
    
    def __init__(self, ventrata_file: str, monday_file: str = None, 
                 update_file: str = None, output_dir: str = None):
        """
        Initialize worker.
        
        Args:
            ventrata_file: Path to Ventrata file
            monday_file: Path to Monday file (optional)
            update_file: Path to update file (optional)
            output_dir: Output directory path
        """
        super().__init__()
        
        self.ventrata_file = ventrata_file
        self.monday_file = monday_file
        self.update_file = update_file
        self.output_dir = output_dir
        self._is_running = True
    
    def run(self):
        """Execute the extraction process."""
        try:
            # Step 1: Import Files
            self.progress_updated.emit('import', 'loading', 'Loading files...')
            
            logger.info(f"Loading Ventrata file: {self.ventrata_file}")
            ventrata_df = load_ventrata(self.ventrata_file)
            files_loaded = 1
            
            monday_df = None
            if self.monday_file:
                logger.info(f"Loading Monday file: {self.monday_file}")
                monday_df = load_monday(self.monday_file)
                files_loaded += 1
            
            update_df = None
            update_row_colors = {}
            if self.update_file:
                logger.info(f"Loading update file: {self.update_file}")
                update_df, update_row_colors = load_update_file(self.update_file)
                files_loaded += 1
            
            self.progress_updated.emit(
                'import', 'complete', 
                f'✓ Loaded {files_loaded} file{"s" if files_loaded > 1 else ""}'
            )
            
            if not self._is_running:
                return
            
            # Step 2: Merge Lists
            self.progress_updated.emit('merge', 'loading', 'Merging data...')
            
            if monday_df is not None:
                merged_df = merge_data(ventrata_df, monday_df)
                logger.info(f"Merged data: {len(merged_df)} rows")
            else:
                merged_df = ventrata_df
                logger.info("No Monday file - processing Ventrata only")
            
            bookings_count = merged_df['_normalized_order_ref'].nunique() if '_normalized_order_ref' in merged_df.columns else len(merged_df)
            self.progress_updated.emit(
                'merge', 'complete', 
                f'✓ {bookings_count} booking{"s" if bookings_count != 1 else ""}'
            )
            
            if not self._is_running:
                return
            
            # Step 3: Verify Names (Name Extraction & Validation)
            self.progress_updated.emit(
                'verify', 'loading', 
                'Extracting and validating names...'
            )
            
            processor = NameExtractionProcessor(merged_df, monday_df, update_df)
            results_df = processor.process()
            
            if results_df.empty:
                self.error_occurred.emit("No data was extracted!")
                self.progress_updated.emit('verify', 'pending', '')
                return
            
            entries_count = len(results_df)
            errors_count = results_df['Error'].ne('').sum() if 'Error' in results_df.columns else 0
            
            self.progress_updated.emit(
                'verify', 'complete', 
                f'✓ {entries_count} entries ({errors_count} errors)'
            )
            
            # Collect warnings
            if errors_count > 0:
                # Sample some errors as warnings
                error_df = results_df[results_df['Error'] != '']
                error_types = {}
                for error in error_df['Error'].head(20):  # Limit to first 20
                    for err in str(error).split(' | '):
                        err = err.strip()
                        if err:
                            error_types[err] = error_types.get(err, 0) + 1
                
                for error_type, count in list(error_types.items())[:5]:  # Top 5
                    self.warning_added.emit(f"{error_type} ({count} occurrence{'s' if count > 1 else ''})")
            
            if not self._is_running:
                return
            
            # Step 4: Export List
            self.progress_updated.emit('export', 'loading', 'Saving results...')
            
            # Determine output file path
            if self.output_dir:
                import os
                base_output_file = os.path.join(self.output_dir, "names_output.xlsx")
            else:
                base_output_file = "names_output.xlsx"
            
            output_file = get_next_available_filename(base_output_file)
            
            logger.info(f"Saving results to: {output_file}")
            save_results_to_excel(results_df, output_file, update_row_colors=update_row_colors)
            
            self.progress_updated.emit(
                'export', 'complete', 
                f'✓ Saved to {output_file.split("/")[-1]}'
            )
            
            # Success!
            success_message = f"Successfully processed {entries_count} entries"
            if errors_count > 0:
                success_message += f" ({errors_count} with errors)"
            
            self.finished.emit(True, success_message, output_file)
            
        except FileNotFoundError as e:
            error_msg = f"File not found: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            self.finished.emit(False, error_msg, "")
            
        except Exception as e:
            error_msg = f"Error during processing: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            self.finished.emit(False, error_msg, "")
    
    def stop(self):
        """Stop the worker thread."""
        self._is_running = False
        logger.info("Worker thread stop requested")

