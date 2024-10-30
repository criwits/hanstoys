import fitz
import tempfile
import os
import argparse

def get_pdf_page_sizes(pdf_path):
    doc = fitz.open(pdf_path)
    sizes = []
    for page_num in range(len(doc)):
        with tempfile.NamedTemporaryFile() as temp:
            temp_doc = fitz.open()
            temp_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
            temp_doc.save(temp.name)
            temp_doc.close()
            size = os.path.getsize(temp.name)
            sizes.append(size)

        
    doc.close()
    return sizes

def byte_to_human_readable(byte):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if byte < 1024:
            return f"{byte:.2f} {unit}"
        byte /= 1024

    return f"{byte:.2f} PB"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="pdfpgsz - Get the (file, not geometry) size of each page in a PDF file.")
    parser.add_argument("pdf", help="The path to the PDF")
    parser.add_argument("--human-readable", "-H", action="store_true", help="print the sizes in human-readable format", default=False)
    parser.add_argument("--sort", "-s", action="store_true", help="sort the sizes in ascending order", default=False)
    parser.add_argument("--reverse", "-r", action="store_true", help="sort the sizes in descending order", default=False)
    args = parser.parse_args()

    sizes = get_pdf_page_sizes(args.pdf)
    sizes = [(i + 1, size) for i, size in enumerate(sizes)]

    if args.sort:
        sizes.sort(key=lambda x: x[1], reverse=args.reverse)

    for i, size in sizes:
        if args.human_readable:
            print_size = byte_to_human_readable(size)
        else:
            print_size = f"{size} B"
        print(f"Page {i:>4}: {print_size:>10}")

    total_size = sum(size for _, size in sizes)
    real_total_size = os.path.getsize(args.pdf)

    if args.human_readable:
        print_size = byte_to_human_readable(total_size)
        real_print_size = byte_to_human_readable(real_total_size)
    else:
        print_size = f"{total_size} B"
        real_print_size = f"{real_total_size} B"

    print("-" * 25)
    print(f"Total: {print_size:>10}")
    print(f"Real:  {real_print_size:>10}")