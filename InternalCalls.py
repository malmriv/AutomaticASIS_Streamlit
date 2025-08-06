import csv
import os
import sys

def normalize_address(address):
    if not address:
        return ''
    return address.strip().rstrip('/').lower()

def process_csv_file(file_path, output_dir):
    rows = []

    with open(file_path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)

        # Ensure UID is the first column
        if headers[0] != "UID":
            raise ValueError("Expected first column to be 'UID'.")

        # Add new columns if not already present
        if "CallsIflow" not in headers:
            headers.append("CallsIflow")
        if "IsCalledByIflow" not in headers:
            headers.append("IsCalledByIflow")

        for row in reader:
            while len(row) < len(headers):
                row.append("")
            rows.append(row)

    # Index helpers
    idx_uid = headers.index("UID")
    idx_type = headers.index("AdapterType")
    idx_dir = headers.index("AdapterDirection")
    idx_addr = headers.index("AdapterAddress")
    idx_calls = headers.index("CallsIflow")
    idx_called_by = headers.index("IsCalledByIflow")

    # Step 1: Build mapping of address → receiver UIDs
    receiver_map = {}
    for row in rows:
        if row[idx_type] == "ProcessDirect" and row[idx_dir] == "Receiver":
            addr = normalize_address(row[idx_addr])
            if addr:
                receiver_map[addr] = row[idx_uid]

    # Step 2: Match senders to receivers by address
    for row in rows:
        if row[idx_type] == "ProcessDirect" and row[idx_dir] == "Sender":
            addr = normalize_address(row[idx_addr])
            if addr in receiver_map:
                sender_uid = row[idx_uid]
                receiver_uid = receiver_map[addr]

                # Update receiver
                for r in rows:
                    if r[idx_uid] == receiver_uid:
                        r[idx_called_by] = f"{r[idx_called_by]}, {sender_uid}".strip(", ")
                        break

                # Update sender
                row[idx_calls] = f"{row[idx_calls]}, {receiver_uid}".strip(", ")

    # Write to temp dir
    output_file = "final_output.csv"
    output_path = os.path.join(output_dir, output_file)

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(headers)
        writer.writerows(rows)

    # Return path for app.py (stdout)
    print(output_path)

def main():
    if len(sys.argv) < 2:
        print("❌ No input directory provided.", file=sys.stderr)
        return

    input_dir = sys.argv[1]
    csv_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.csv')]
    if not csv_files:
        print("⚠️ No CSV files found in directory.", file=sys.stderr)
        return

    # We assume processing only the first CSV
    file_path = os.path.join(input_dir, csv_files[0])
    process_csv_file(file_path, input_dir)

if __name__ == "__main__":
    main()
