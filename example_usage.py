"""
Example usage of the Names Generation System.

This script demonstrates how to use the name extraction system
programmatically without running main.py.
"""

import pandas as pd
from data_loader import load_ventrata, load_monday, load_update_file, merge_data
from processor import NameExtractionProcessor

######TEST#######################
# filepath = "/Users/navidabasi/Downloads/tickets.xlsx"
######TEST#######################


def example_basic_usage():
    """
    Example 1: Basic usage with Ventrata file only.
    """
    print("\n" + "="*80)
    print("Example 1: Processing Ventrata file only")
    print("="*80)
    
    # Load Ventrata data
    ventrata_file = "path/to/ventrata.xlsx"
    ventrata_df = load_ventrata(ventrata_file)
    
    # Process without Monday data
    processor = NameExtractionProcessor(ventrata_df, monday_df=None)
    results_df = processor.process()
    
    # Display results
    print(f"\nProcessed {len(results_df)} entries")
    print("\nSample results:")
    print(results_df[['Full Name', 'Order Reference', 'Unit Type', 'Error']].head())
    
    # Save to Excel
    results_df.to_excel("ventrata_only_results.xlsx", index=False)
    print("\nResults saved to: ventrata_only_results.xlsx")
    
    return results_df


def example_with_monday():
    """
    Example 2: Processing with both Ventrata and Monday files.
    """
    print("\n" + "="*80)
    print("Example 2: Processing Ventrata + Monday files")
    print("="*80)
    
    # Load both files
    ventrata_file = "path/to/ventrata.xlsx"
    monday_file = "path/to/monday.xlsx"
    
    ventrata_df = load_ventrata(ventrata_file)
    monday_df = load_monday(monday_file)
    
    # Merge data
    merged_df = merge_data(ventrata_df, monday_df)
    print(f"Merged data: {len(merged_df)} rows")
    
    # Process
    processor = NameExtractionProcessor(ventrata_df, monday_df)
    results_df = processor.process()
    
    # Display results
    print(f"\nProcessed {len(results_df)} entries")
    print("\nColumns available:")
    print(results_df.columns.tolist())
    
    # Filter entries with errors
    errors_df = results_df[results_df['Error'] != '']
    print(f"\nEntries with errors: {len(errors_df)}")
    
    if not errors_df.empty:
        print("\nTop errors:")
        print(errors_df[['Full Name', 'Order Reference', 'Error']].head(10))
    
    # Save results
    results_df.to_excel("full_results.xlsx", index=False)
    print("\nResults saved to: full_results.xlsx")
    
    return results_df


def example_error_analysis():
    """
    Example 3: Analyzing error types.
    """
    print("\n" + "="*80)
    print("Example 3: Error Analysis")
    print("="*80)
    
    # Process data (assuming files exist)
    ventrata_df = load_ventrata("path/to/ventrata.xlsx")
    processor = NameExtractionProcessor(ventrata_df)
    results_df = processor.process()
    
    # Analyze errors
    errors_df = results_df[results_df['Error'] != '']
    
    # Count error types
    error_types = {}
    for error in errors_df['Error']:
        for err in str(error).split(' | '):
            err = err.strip()
            if err:
                error_types[err] = error_types.get(err, 0) + 1
    
    # Display error statistics
    print(f"\nTotal entries: {len(results_df)}")
    print(f"Entries with errors: {len(errors_df)}")
    print(f"Success rate: {((len(results_df) - len(errors_df)) / len(results_df) * 100):.1f}%")
    
    print("\nError type breakdown:")
    for error_type, count in sorted(error_types.items(), key=lambda x: -x[1]):
        percentage = (count / len(results_df)) * 100
        print(f"  {error_type}: {count} ({percentage:.1f}%)")
    
    # Export errors separately
    errors_df.to_excel("errors_only.xlsx", index=False)
    print("\nErrors saved to: errors_only.xlsx")
    
    return error_types


def example_with_update_file():
    """
    Example 4: Using update file to reuse previously extracted names.
    
    This is useful when you have:
    - A new Ventrata file with some bookings you've already processed
    - You want to only extract names for new bookings
    - Update notes for existing bookings without re-extracting names
    """
    print("\n" + "="*80)
    print("Example 4: Using Update File")
    print("="*80)
    
    # Load files
    ventrata_file = "path/to/new_ventrata.xlsx"  # New Ventrata with old + new bookings
    update_file = "path/to/previous_output.xlsx"  # Previously generated output
    monday_file = "path/to/monday.xlsx"  # Optional
    
    ventrata_df = load_ventrata(ventrata_file)
    update_df = load_update_file(update_file)
    monday_df = load_monday(monday_file) if monday_file else None
    
    print(f"Loaded {len(ventrata_df)} Ventrata rows")
    print(f"Loaded {len(update_df)} previously extracted entries")
    
    # Process with update file
    processor = NameExtractionProcessor(ventrata_df, monday_df, update_df)
    results_df = processor.process()
    
    print(f"\nProcessed {len(results_df)} entries")
    print("  - Reused names from update file for existing IDs")
    print("  - Extracted names for new IDs only")
    print("  - Updated notes from new Ventrata for all bookings")
    
    # Check for ID mismatches
    mismatch_df = results_df[results_df['Error'].str.contains('does not match', na=False)]
    if not mismatch_df.empty:
        print(f"\nWarning: {len(mismatch_df)} bookings have ID mismatches")
        print("These bookings were re-extracted and flagged")
    
    # Save results
    results_df.to_excel("updated_results.xlsx", index=False)
    print("\nResults saved to: updated_results.xlsx")
    
    return results_df


def example_filter_by_reseller():
    """
    Example 5: Process and filter by reseller type.
    """
    print("\n" + "="*80)
    print("Example 5: Filter by Reseller")
    print("="*80)
    
    # Process data
    ventrata_df = load_ventrata("path/to/ventrata.xlsx")
    processor = NameExtractionProcessor(ventrata_df)
    results_df = processor.process()
    
    # Filter by reseller
    reseller_types = results_df['Reseller'].unique()
    print(f"\nFound {len(reseller_types)} reseller types:")
    for reseller in reseller_types:
        count = len(results_df[results_df['Reseller'] == reseller])
        print(f"  {reseller}: {count} entries")
    
    # Export GYG bookings only
    gyg_df = results_df[results_df['Reseller'].str.contains('GetYourGuide', na=False)]
    print(f"\nGYG bookings: {len(gyg_df)}")
    gyg_df.to_excel("gyg_only_results.xlsx", index=False)
    
    return results_df


if __name__ == "__main__":
    print("Names Generation System - Example Usage")
    print("=" * 80)
    print("\nThis file contains example usage patterns.")
    print("Update the file paths and uncomment the example you want to run.")
    print("\nAvailable examples:")
    print("  1. example_basic_usage() - Process Ventrata only")
    print("  2. example_with_monday() - Process with Monday data")
    print("  3. example_error_analysis() - Analyze error statistics")
    print("  4. example_with_update_file() - Reuse previously extracted names")
    print("  5. example_filter_by_reseller() - Filter by platform")
    print("\n" + "=" * 80)
    
    # Uncomment the example you want to run:
    # example_basic_usage()
    # example_with_monday()
    # example_error_analysis()
    # example_with_update_file()
    # example_filter_by_reseller()

