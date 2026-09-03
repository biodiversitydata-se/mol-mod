#!/usr/bin/env python3
"""
Rebuild the README.txt citation in mol-mod export zips. Pure stdlib.

For every *.zip in DIR (default: current dir), the "Citation:" line in
README.txt is replaced by:

    <resource citation from that zip's eml.xml>  https://doi.org/<DOI>

  * The citation body (authors, year, title, Version X.Y, publisher, IPT
    resource URL) is taken verbatim from eml.xml, so it always matches the
    exported IPT version.
  * The DOI is carried over from the zip's current README citation line
    (it is not in the EML).
  * The trailing "accessed ... on <date>." clause is dropped - a named
    version already identifies the content, and the date was GBIF's stale
    harvest date, not the export date.

Only rewrites a zip whose README actually changed. Owner/mode/mtime are
preserved. Prints a summary of what changed.

Usage:  fix-export-readme.py [-n] [DIR]
          -n / --dry-run   show what would change, write nothing
"""
import html
import os
import re
import sys
import zipfile

CIT_LINE = re.compile(r'^Citation:.*$', re.M)
EML_CITATION = re.compile(r'<citation\b([^>]*)>(.*?)</citation>', re.S)
VERSION = re.compile(r'\bVersion\s+([0-9]+(?:\.[0-9]+)+)')
PKG_VERSION = re.compile(r'packageId="[^"]*/v([0-9]+(?:\.[0-9]+)+)"')
DOI_URL = re.compile(r'https?://(?:dx\.)?doi\.org/(10\.\d{4,}/\S+)')


def resource_citation(eml: str):
    """The <citation> element that has no identifier= attribute."""
    for attrs, body in EML_CITATION.findall(eml):
        if 'identifier' not in attrs:
            return html.unescape(re.sub(r'\s+', ' ', body)).strip()
    return None


def pick_doi(citation_line: str):
    """Dataset DOI from the current README citation line (prefer GBIF's)."""
    dois = [d.rstrip('.') for d in DOI_URL.findall(citation_line)]
    if not dois:
        return None
    for d in dois:
        if d.startswith('10.15468/'):
            return d
    return dois[0]


def rebuild(readme: str, eml: str):
    """Return (new_readme, note) or (readme, reason) if nothing to do."""
    cit = resource_citation(eml)
    if not cit:
        return readme, 'skip (no EML citation)'

    # packageId is the authoritative published version; the free-text
    # "Version X.Y" inside <citation> is sometimes out of sync.
    verfix = ''
    pkg = PKG_VERSION.search(eml)
    cver = VERSION.search(cit)
    if pkg and cver and pkg.group(1) != cver.group(1):
        pv, cv = pkg.group(1), cver.group(1)
        cit = re.sub(rf'\bVersion {re.escape(cv)}\b', f'Version {pv}', cit)
        cit = re.sub(rf'([?&]v=){re.escape(cv)}\b', rf'\g<1>{pv}', cit)
        verfix = f'citation ver {cv}!=packageId {pv} (used {pv}); '

    m = CIT_LINE.search(readme)
    old_line = m.group(0) if m else ''
    doi = pick_doi(old_line)

    new_line = f'Citation: {cit}'
    if doi and doi not in cit:
        new_line += f' https://doi.org/{doi}'

    notes = []
    if not VERSION.search(cit):
        notes.append('no version in EML')
    if not doi:
        notes.append('no DOI in README')
    note = '; '.join(notes)

    if not m:
        # no Citation: line to replace - leave the file alone
        return readme, (verfix + (note or 'no Citation line')).strip()
    if new_line == old_line:
        return readme, (verfix + (note or 'already ok')).strip()

    new_readme = readme[:m.start()] + new_line + readme[m.end():]
    ov = VERSION.search(old_line)
    nv = VERSION.search(new_line)
    vtag = ''
    if ov and nv and ov.group(1) != nv.group(1):
        vtag = f'{ov.group(1)}->{nv.group(1)} '
    return new_readme, (vtag + verfix + (note or 'rebuilt')).strip()


def rewrite_zip(path: str, new_readme: str):
    st = os.stat(path)
    tmp = path + '.tmp'
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, 'w') as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            if info.filename == 'README.txt':
                data = new_readme.encode('utf-8')
            zout.writestr(info, data, compress_type=info.compress_type)
    os.replace(tmp, path)
    try:
        os.chown(path, st.st_uid, st.st_gid)
    except (PermissionError, OSError):
        pass
    os.chmod(path, st.st_mode)
    os.utime(path, (st.st_atime, st.st_mtime))


def main():
    dry = False
    d = '.'
    for a in sys.argv[1:]:
        if a in ('-n', '--dry-run'):
            dry = True
        elif a in ('-h', '--help'):
            print(__doc__)
            return 0
        else:
            d = a
    if not os.path.isdir(d):
        print(f'No such directory: {d}', file=sys.stderr)
        return 1

    zips = sorted(f for f in os.listdir(d) if f.endswith('.zip'))
    if not zips:
        print(f'No .zip files in {d}', file=sys.stderr)
        return 0

    changed = 0
    print(f'{"ZIP":40}  {"RESULT":22}  NOTE')
    print(f'{"---":40}  {"------":22}  ----')
    for name in zips:
        path = os.path.join(d, name)
        try:
            with zipfile.ZipFile(path) as zf:
                members = set(zf.namelist())
                if 'eml.xml' not in members or 'README.txt' not in members:
                    print(f'{name:40}  {"skip":22}  no eml.xml/README.txt')
                    continue
                eml = zf.read('eml.xml').decode('utf-8', 'replace')
                readme = zf.read('README.txt').decode('utf-8', 'replace')
        except zipfile.BadZipFile:
            print(f'{name:40}  {"skip":22}  bad zip')
            continue

        new_readme, note = rebuild(readme, eml)
        if new_readme != readme:
            if not dry:
                rewrite_zip(path, new_readme)
                res = 'rebuilt'
            else:
                res = 'would rebuild'
            changed += 1
        else:
            res = 'no change'
        print(f'{name:40}  {res:22}  {note}')

    print()
    tail = 'would be changed (dry run)' if dry else 'changed'
    print(f'{changed} of {len(zips)} zip(s) {tail}.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
