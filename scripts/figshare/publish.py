#!/usr/bin/env python3
"""
"""

import os
import zipfile


def generate_manifest(zip):
    zip_size = os.path.getsize(zip)
    zip_name = os.path.basename(zip)

    with zipfile.ZipFile(zip, 'r') as zip_ref:
        files = zip_ref.namelist()

        # Sort on file extension then basename
        files.sort(key=lambda x: (x.split('.')[-1], x.split('/')[-1]))

        def convert_size(size):
            size_kb = size / 1024
            if size_kb < 1024:
                return f"{size_kb:.0f} kB"  # No decimals for kB
            else:
                return f"{size_kb / 1024:.1f} MB"

        manifest_content = f"{zip_name} ({convert_size(zip_size)}):\n"
        for filename in files:
            size = zip_ref.getinfo(filename).file_size
            manifest_content += f"{filename} ({convert_size(size)})\n"

    with open("MANIFEST.txt", "w") as manifest_file:
        print(f"Writing manifest for {os.path.basename(zip)}")
        manifest_file.write(manifest_content)


# Example usage:
zip = '../../exports/KTH-2013-Baltic-16S.zip'
generate_manifest(zip)
