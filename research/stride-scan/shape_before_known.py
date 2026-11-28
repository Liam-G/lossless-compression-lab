"""Our shape step first (reversible re-layout), known compressor after."""
import subprocess, sys, os
def sizes(b, tag):
    open('t', 'wb').write(b)
    r = {'xz': len(subprocess.run(['xz', '-9e', '-c', '-T1', 't'], capture_output=True).stdout),
         'bzip2': len(subprocess.run(['bzip2', '-9', '-c', 't'], capture_output=True).stdout),
         'brotli': len(subprocess.run(['brotli', '-q', '11', '-c', 't'], capture_output=True).stdout)}
    if os.path.exists('t.7z'): os.remove('t.7z')
    subprocess.run(['7z', 'a', '-bd', '-bso0', '-t7z', '-m0=PPMd:mem=512m:o=16', 't.7z', 't'], check=True)
    r['ppmd'] = os.path.getsize('t.7z')
    print(f"{tag:42} " + '  '.join(f"{k} {v:>8,}" for k, v in r.items()), flush=True)
for path, w in [(os.path.join(os.environ.get('CORPUS', '../corpus'), 'canterbury/kennedy.xls'), 13),
                (os.path.join(os.environ.get('CORPUS', '../corpus'), 'canterbury/ptt5'), 216)]:
    d = open(path, 'rb').read(); name = os.path.basename(path)
    sizes(d, f'{name} as is')
    cols = b''.join(d[i::w] for i in range(w))                       # read column by column
    sizes(cols, f'{name} column by column (width {w})')
    dl = bytes(d[:w]) + bytes((d[i] - d[i - w]) & 255 for i in range(w, len(d)))   # minus the byte one row up
    sizes(dl, f'{name} minus row above (width {w})')
    sizes(b''.join(dl[i::w] for i in range(w)), f'{name} minus row above, then columns')
