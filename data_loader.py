"""
Data loading and merging utilities.

Handles:
- Loading Ventrata Excel files
- Loading Monday Excel files
- Merging Ventrata and Monday data on Order Reference
"""

import pandas as pd
import logging
import os

from utils.normalization import normalize_ref, standardize_column_names

logger = logging.getLogger(__name__)



def load_ventrata(filepath):

    """
    Load Ventrata Excel file with case-insensitive column handling.
    
    Expected columns:
    - Booking Reference, Order Reference, Customer, STATUS, Product
    - Travel Date, Booking Date, UNIT, Ticket Customer First Name
    - Ticket Customer Last Name, Reseller, Public Notes, Private Notes
    - Product Tags, Product Code, Customer Country, Tour Time
    - Booking Type, ID
    
    Args:
        filepath: Path to Ventrata Excel file
        
    Returns:
        pd.DataFrame: Loaded Ventrata data with standardized columns
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If required columns are missing
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Ventrata file not found: {filepath}")
    
    logger.info(f"Loading Ventrata data from: {filepath}")
    
    # Load Excel file
    df = pd.read_excel(filepath)
    
    logger.info(f"Loaded {len(df)} rows from Ventrata file")
    logger.info(f"Original columns: {list(df.columns)}")
    
    # Create column mapping for case-insensitive access
    column_map = standardize_column_names(df)
    
    # Check for critical columns (case-insensitive)
    critical_columns = ['order reference', 'reseller', 'unit', 'ticket customer first name', 'ticket customer last name', 'public notes', 'private notes']
    missing_columns = []
    
    for col in critical_columns:
        if col not in column_map:
            missing_columns.append(col)
    
    if missing_columns:
        logger.error(f"Missing critical columns in Ventrata file: {missing_columns}")
        logger.error(f"Available columns: {list(df.columns)}")
        raise ValueError(f"Missing critical columns: {missing_columns}")
    
    # Add normalized order reference column for merging
    order_ref_col = column_map.get('order reference')
    if order_ref_col:
        df['_normalized_order_ref'] = df[order_ref_col].apply(normalize_ref)
        logger.info(f"Added normalized order reference column")
    
    logger.info(f"Successfully loaded Ventrata data with {len(df)} rows")
    
    return df


def load_monday(filepath):
    """
    Load Monday Excel file with case-insensitive column handling.
    
    Expected columns:
    - Client, Order Reference, Change By, Report By, Travel Date
    - Tour Time, Product Code, Ticket Time, Ticket PNR
    - Codice Prenotazione, Sigillo, Note, TIX SOURCE, TICKET GROUP
    - Missing Names, Adult, Child, Infant, Youth, Ridotto, Private Notes
    
    Args:
        filepath: Path to Monday Excel file
        
    Returns:
        pd.DataFrame: Loaded Monday data with standardized columns
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If required columns are missing
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Monday file not found: {filepath}")
    
    logger.info(f"Loading Monday data from: {filepath}")
    
    # Load Excel file (Monday exports typically have header at row 3, index 2)
    try:
        df = pd.read_excel(filepath, header=2)
    except Exception:
        # Fallback to default header row
        df = pd.read_excel(filepath)
    
    logger.info(f"Loaded {len(df)} rows from Monday file")
    logger.info(f"Original columns: {list(df.columns)}")
    
    # Create column mapping for case-insensitive access
    column_map = standardize_column_names(df)
    
    # Check for critical columns (case-insensitive)
    critical_columns = ['order reference']
    missing_columns = []
    
    for col in critical_columns:
        if col not in column_map:
            missing_columns.append(col)
    
    if missing_columns:
        logger.error(f"Missing critical columns in Monday file: {missing_columns}")
        logger.error(f"Available columns: {list(df.columns)}")
        raise ValueError(f"Missing critical columns: {missing_columns}")
    
    # Add normalized order reference column for merging
    order_ref_col = column_map.get('order reference')
    if order_ref_col:
        df['_normalized_order_ref'] = df[order_ref_col].apply(normalize_ref)
        logger.info(f"Added normalized order reference column")
    
    # Filter out header rows and invalid data
    df = df.dropna(subset=[order_ref_col])
    df = df[df[order_ref_col] != 'Order Reference']
    
    logger.info(f"Successfully loaded Monday data with {len(df)} rows (after filtering)")
    
    return df


def load_update_file(filepath):
    """
    Load update file (previously generated output) for reusing extracted data.
    
    Update file has the same format as output Excel with columns:
    - Full Name, ID, Order Reference, Unit Type, Travel Date, etc.
    
    Args:
        filepath: Path to update file Excel
        
    Returns:
        pd.DataFrame: Loaded update file data with standardized columns
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If required columns are missing
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Update file not found: {filepath}")
    
    logger.info(f"Loading update file from: {filepath}")
    
    # Load Excel file
    df = pd.read_excel(filepath)
    
    logger.info(f"Loaded {len(df)} rows from update file")
    logger.info(f"Original columns: {list(df.columns)}")
    
    # Create column mapping for case-insensitive access
    column_map = standardize_column_names(df)
    
    # Check for critical columns (case-insensitive)
    critical_columns = ['full name', 'id', 'order reference', 'unit type']
    missing_columns = []
    
    for col in critical_columns:
        if col not in column_map:
            missing_columns.append(col)
    
    if missing_columns:
        logger.error(f"Missing critical columns in update file: {missing_columns}")
        logger.error(f"Available columns: {list(df.columns)}")
        raise ValueError(f"Missing critical columns: {missing_columns}")
    
    # Forward-fill merged cells (e.g., Order Reference, Error) to ensure each row has values
    order_ref_col = column_map.get('order reference')
    if order_ref_col:
        df[order_ref_col] = df[order_ref_col].fillna(method='ffill')
    
    error_col = column_map.get('error')
    if error_col:
        df[error_col] = df[error_col].fillna(method='ffill')
    
    private_notes_col = column_map.get('private notes')
    if private_notes_col:
        df[private_notes_col] = df[private_notes_col].fillna(method='ffill')
    
    # Add normalized order reference for matching
    if order_ref_col:
        df['_normalized_order_ref'] = df[order_ref_col].apply(normalize_ref)
        logger.info(f"Added normalized order reference column")
    
    logger.info(f"Successfully loaded update file with {len(df)} rows")
    
    return df


def merge_data(ventrata_df, monday_df=None):
    """
    Merge Ventrata and Monday data on normalized Order Reference.
    
    Strategy:
    - If Monday data provided: Inner join on normalized order reference
    - Keep ALL columns from both sources
    - Handle column conflicts by prefixing with source name
    - If no Monday data: Return Ventrata as-is
    
    Args:
        ventrata_df: Ventrata DataFrame (required)
        monday_df: Monday DataFrame (optional)
        
    Returns:
        pd.DataFrame: Merged data or Ventrata-only data
    """
    if monday_df is None:
        logger.info("No Monday data provided - using Ventrata only")
        return ventrata_df.copy()
    
    logger.info(f"Merging Ventrata ({len(ventrata_df)} rows) with Monday ({len(monday_df)} rows)")
    
    # Check if both have normalized reference column
    if '_normalized_order_ref' not in ventrata_df.columns:
        logger.error("Ventrata data missing _normalized_order_ref column")
        raise ValueError("Ventrata data must have _normalized_order_ref column")
    
    if '_normalized_order_ref' not in monday_df.columns:
        logger.error("Monday data missing _normalized_order_ref column")
        raise ValueError("Monday data must have _normalized_order_ref column")
    
    # Find common columns (excluding the merge key)
    ventrata_cols = set(ventrata_df.columns) - {'_normalized_order_ref'}
    monday_cols = set(monday_df.columns) - {'_normalized_order_ref'}
    common_cols = ventrata_cols & monday_cols
    
    if common_cols:
        logger.info(f"Found {len(common_cols)} common columns: {sorted(common_cols)}")
        # Rename common columns to avoid conflicts
        ventrata_df = ventrata_df.copy()
        monday_df = monday_df.copy()
        
        for col in common_cols:
            ventrata_df = ventrata_df.rename(columns={col: f'ventrata_{col}'})
            monday_df = monday_df.rename(columns={col: f'monday_{col}'})
    
    # Perform merge
    merged_df = pd.merge(
        ventrata_df,
        monday_df,
        on='_normalized_order_ref',
        how='inner',
        suffixes=('_ventrata', '_monday')
    )
    
    logger.info(f"Merged data contains {len(merged_df)} rows")
    logger.info(f"Merged columns: {list(merged_df.columns)}")
    
    return merged_df


def get_ventrata_column_map(df):
    """
    Get mapping of standard column names to actual Ventrata column names.
    
    Args:
        df: Ventrata DataFrame
        
    Returns:
        dict: Mapping of standard names to actual column names
    """
    column_map = standardize_column_names(df)
    
    # Map to standard names
    standard_map = {
        'order_reference': column_map.get('order reference'),
        'booking_reference': column_map.get('booking reference'),
        'customer': column_map.get('customer'),
        'status': column_map.get('status'),
        'product': column_map.get('product'),
        'travel_date': column_map.get('travel date'),
        'booking_date': column_map.get('booking date'),
        'unit': column_map.get('unit'),
        'first_name': column_map.get('ticket customer first name'),
        'last_name': column_map.get('ticket customer last name'),
        'reseller': column_map.get('reseller'),
        'public_notes': column_map.get('public notes'),
        'private_notes': column_map.get('private notes'),
        'product_tags': column_map.get('product tags'),
        'product_code': column_map.get('product code'),
        'customer_country': column_map.get('customer country'),
        'tour_time': column_map.get('tour time'),
        'booking_type': column_map.get('booking type'),
        'id': column_map.get('id')
    }
    
    # Remove None values
    return {k: v for k, v in standard_map.items() if v is not None}


def get_monday_column_map(df):
    """
    Get mapping of standard column names to actual Monday column names.
    
    Args:
        df: Monday DataFrame
        
    Returns:
        dict: Mapping of standard names to actual column names
    """
    column_map = standardize_column_names(df)
    
    # Map to standard names
    standard_map = {
        'client': column_map.get('client'),
        'order_reference': column_map.get('order reference'),
        'change_by': column_map.get('change by'),
        'report_by': column_map.get('report by'),
        'travel_date': column_map.get('travel date'),
        'tour_time': column_map.get('tour time'),
        'product_code': column_map.get('product code'),
        'ticket_time': column_map.get('ticket time'),
        'ticket_pnr': column_map.get('ticket pnr'),
        'codice_prenotazione': column_map.get('codice prenotazione'),
        'sigillo': column_map.get('sigillo'),
        'note': column_map.get('note'),
        'tix_source': column_map.get('tix source'),
        'ticket_group': column_map.get('ticket group'),
        'missing_names': column_map.get('missing names'),
        'adult': column_map.get('adult'),
        'child': column_map.get('child'),
        'infant': column_map.get('infant'),
        'youth': column_map.get('youth'),
        'ridotto': column_map.get('ridotto'),
        'private_notes': column_map.get('private notes')
    }
    
    # Remove None values
    return {k: v for k, v in standard_map.items() if v is not None}

