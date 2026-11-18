#!/usr/bin/env python3
"""Run the EPA three-program sample, preserving originals and writing diffs."""
import difflib
import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile


def safe_extract(archive, target):
    target = target.resolve()
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            path = (target / item.filename).resolve()
            if not path.is_relative_to(target):
                raise RuntimeError('Percorso ZIP non consentito')
            if (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise RuntimeError('Link simbolico nello ZIP non consentito')
        z.extractall(target)


def find_named(root, name):
    matches = [p for p in root.rglob('*') if p.is_file() and p.name.lower() == name.lower()]
    if len(matches) != 1:
        raise RuntimeError(f'Atteso un solo {name}, trovati {len(matches)}')
    return matches[0]


def case_path(token, base):
    """Resolve existing path components without assuming case-insensitive APFS."""
    token = token.replace('\\', '/')
    if ':' in token or token.startswith('/'):
        raise RuntimeError(f'Percorso assoluto nel sample: {token}; adattarlo prima del run')
    current = base
    result = []
    for part in token.split('/'):
        if part in ('.', '..', ''):
            result.append(part)
            current = current / (part or '.')
            continue
        if current.is_dir():
            matches = [x.name for x in current.iterdir() if x.name.casefold() == part.casefold()]
            if len(matches) == 1:
                part = matches[0]
        result.append(part)
        current = current / part
    return '/'.join(result)


def adapt_inputs(root, report):
    for path in root.rglob('*'):
        if path.suffix.lower() != '.inp':
            continue
        text = path.read_text(encoding='latin-1')
        def replace(match):
            token = match.group(0)
            quote = token[0] if token[:1] in ('"', "'") else ''
            value = token[1:-1] if quote else token
            # Touch only file-like tokens, never physical/numerical settings.
            if not re.search(r'\.[A-Za-z][A-Za-z0-9_]{0,9}$', value):
                return token
            adapted = case_path(value, path.parent)
            return quote + adapted + quote
        lines = []
        for line in text.splitlines(keepends=True):
            if line.lstrip().startswith('**'):
                lines.append(line)
            else:
                lines.append(re.sub(r'"[^"\n]*"|\x27[^\x27\n]*\x27|[^\s"\x27]+', replace, line))
        new = ''.join(lines)
        if new != text:
            with report.open('a') as out:
                out.writelines(difflib.unified_diff(text.splitlines(True), new.splitlines(True),
                                                   fromfile=str(path), tofile='adattato-macOS'))
        path.write_text(new, encoding='latin-1', newline='\n')


def remove_outputs(directory, names):
    for p in directory.iterdir():
        if p.is_file() and p.name.lower() in names:
            p.unlink()


def require_output(directory, name, allow_empty=False):
    matches = [p for p in directory.iterdir() if p.name.lower() == name.lower()]
    if len(matches) != 1 or not matches[0].is_file():
        raise RuntimeError(f'Output non prodotto: {directory / name}')
    p = matches[0]
    if not allow_empty and p.stat().st_size == 0:
        raise RuntimeError(f'Output vuoto: {p}')
    return p


def main(package, url):
    reports = package / 'reports'
    reports.mkdir(exist_ok=True)
    archive = Path('diagnostics/sample.zip')
    archive.parent.mkdir(exist_ok=True)
    # Cache only within this run; the second invocation tests relocation.
    if not archive.exists():
        request = urllib.request.Request(url, headers={'User-Agent': 'AERMOD-teaching-build/1.0'})
        with urllib.request.urlopen(request, timeout=180) as response, archive.open('wb') as out:
            shutil.copyfileobj(response, out)
    (reports / 'sample-origin.txt').write_text(
        f'{url}\nSHA256 {hashlib.sha256(archive.read_bytes()).hexdigest()}\n')
    sample = package / 'SampleRun'
    if sample.exists():
        shutil.rmtree(sample)
    sample.mkdir()
    safe_extract(archive, sample)
    for p in list(sample.rglob('*')):
        if p.suffix.lower() == '.exe':
            p.unlink()
    amap = find_named(sample, 'aermap.inp').parent
    amet = find_named(sample, 'aermet1.inp').parent
    amod = find_named(sample, 'aermod.inp').parent
    find_named(sample, 'aermet2.inp')
    (reports / 'input-adaptations.diff').write_text('')
    adapt_inputs(sample, reports / 'input-adaptations.diff')
    remove_outputs(amap, {'aermap.src','aermap.rec','aermap.out','errors.out'})
    remove_outputs(amet, {'aermet.sfc','aermet.pfl','aermet.out','errors.out'})
    remove_outputs(amod, {'aermod.out','aermod.sum','errors.out'})
    stages = [('aermap', amap, [], 'aermap'),
              ('aermet', amet, [find_named(sample,'aermet1.inp').name], 'aermet-stage1'),
              ('aermet', amet, [find_named(sample,'aermet2.inp').name], 'aermet-stage2'),
              ('aermod', amod, [], 'aermod')]
    for exe, cwd, args, label in stages:
        # Relative loader_path must continue to work after distribution.
        target = cwd / exe
        shutil.copy2(package / exe, target)
        target.chmod(0o755)
        if not (cwd / 'lib').exists():
            shutil.copytree(package / 'lib', cwd / 'lib')
        with (reports / f'{label}.log').open('w') as log:
            subprocess.run([str(target.resolve()), *args], cwd=cwd, stdin=subprocess.DEVNULL,
                           stdout=log, stderr=subprocess.STDOUT, check=True, timeout=1500)
        if exe == 'aermap':
            require_output(cwd, 'aermap.rec')
            require_output(cwd, 'aermap.src', allow_empty=True)
        elif exe == 'aermet' and label.endswith('2'):
            require_output(cwd, 'aermet.sfc')
            require_output(cwd, 'aermet.pfl')
    output = require_output(amod, 'aermod.out')
    text = output.read_text(encoding='latin-1') + (reports/'aermod.log').read_text(encoding='latin-1')
    if not re.search(r'AERMOD\s+Finishes\s+Successfully', text, re.I):
        raise RuntimeError('Manca il messaggio finale di completamento AERMOD')
    fatal_counts = re.findall(r'(\d+)\s+Fatal\s+Error\s+Message', text, re.I)
    if not fatal_counts or any(int(n) for n in fatal_counts):
        raise RuntimeError('Riepilogo errori fatali assente o non nullo')
    version = re.search(r'AERMOD\s*[-–]\s*VERSION\s+(\d+)', text, re.I)
    summary = ['ESECUZIONE COMPLETATA; CONFRONTO NUMERICO DA REVISIONARE.',
               'Versione AERMOD: ' + (version.group(1) if version else 'leggere il log'),
               'Questo controllo non certifica equivalenza numerica con Windows.',
               'Controllare anche warning e log dei due stadi AERMET.', '']
    compared = 0
    for ref in sample.rglob('*'):
        if not ref.is_file() or not re.search(r'[._]org[._]', ref.name, re.I):
            continue
        expected = re.sub(r'_org(?=[._]|$)', '', ref.name, flags=re.I)
        # Some EPA archives use aermod.ORG_out / aermod.ORG_sum.
        expected = re.sub(r'\.org_', '.', expected, flags=re.I)
        candidates = [p for p in ref.parent.iterdir() if p.name.lower() == expected.lower()]
        if len(candidates) != 1 or candidates[0] == ref:
            summary.append(f'Riferimento senza output associato: {ref.relative_to(sample)}')
            continue
        actual = candidates[0]
        a = ref.read_text(encoding='latin-1').splitlines(True)
        b = actual.read_text(encoding='latin-1').splitlines(True)
        diff = ''.join(difflib.unified_diff(a,b,fromfile=ref.name,tofile=actual.name))
        name = '__'.join(actual.relative_to(sample).parts) + '.diff'
        (reports / name).write_text(diff)
        summary.append(f'{actual.relative_to(sample)}: ' + ('IDENTICO' if not diff else 'DIFFERENZE, vedere ' + name))
        compared += 1
    if not compared:
        raise RuntimeError('Nessun riferimento _ORG associabile: controllare struttura del sample')
    (reports/'ESITO.txt').write_text('\n'.join(summary) + '\n')
    print('\n'.join(summary))


if __name__ == '__main__':
    try:
        main(Path(sys.argv[1]).resolve(), sys.argv[2])
    except Exception as exc:
        print(f'SAMPLE RUN NON VERIFICATO: {exc}', file=sys.stderr)
        raise
