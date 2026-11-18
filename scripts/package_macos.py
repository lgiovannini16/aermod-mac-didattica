#!/usr/bin/env python3
"""Bundle recursively all non-system Mach-O dependencies and sign ad hoc."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def run(*args):
    return subprocess.check_output(args, text=True)


def deps(path):
    return [line.strip().rsplit(' (compatibility', 1)[0]
            for line in run('otool', '-L', str(path)).splitlines()[1:]]


def rpaths(path):
    lines = run('otool', '-l', str(path)).splitlines()
    return [lines[i + 2].strip().split(' (offset')[0].removeprefix('path ')
            for i, line in enumerate(lines) if line.strip() == 'cmd LC_RPATH']


def system(dep):
    return dep.startswith(('/usr/lib/', '/System/Library/'))


def bundle(source, destination, arch):
    libdir = destination / 'lib'
    libdir.mkdir(parents=True, exist_ok=True)
    copied = {}
    names = {}
    completed = set()

    def resolve(dep, original, exe):
        value = dep.replace('@loader_path', str(original.parent)).replace(
            '@executable_path', str(exe.parent))
        if value.startswith('@rpath/'):
            suffix = value[len('@rpath/'):]
            for rp in rpaths(original) + rpaths(exe):
                root = rp.replace('@loader_path', str(original.parent)).replace(
                    '@executable_path', str(exe.parent))
                candidate = Path(root) / suffix
                if candidate.is_file():
                    return candidate.resolve()
            raise RuntimeError(f'Dipendenza @rpath non risolta: {dep} in {original}')
        candidate = Path(value)
        if not candidate.is_file():
            raise RuntimeError(f'Libreria non trovata: {dep} in {original}')
        return candidate.resolve()

    def process(original, target, exe):
        key = (str(original), str(target))
        if key in completed:
            return
        completed.add(key)
        if arch not in run('lipo', '-archs', str(original)).split():
            raise RuntimeError(f'Architettura {arch} assente: {original}')
        for dep in deps(original):
            if system(dep):
                continue
            resolved = resolve(dep, original, exe)
            # A dylib's first entry can be its own install name.
            if resolved == original.resolve():
                continue
            name = resolved.name
            if name in names and names[name] != resolved:
                raise RuntimeError(f'Collisione nomi librerie: {name}')
            names[name] = resolved
            bundled = libdir / name
            if resolved not in copied:
                shutil.copy2(resolved, bundled)
                bundled.chmod(0o755)
                copied[resolved] = bundled
                process(resolved, bundled, exe)
                subprocess.run(['install_name_tool', '-id', '@loader_path/' + name,
                                str(bundled)], check=True)
            replacement = ('@loader_path/lib/' if target.parent == destination
                           else '@loader_path/') + name
            subprocess.run(['install_name_tool', '-change', dep, replacement,
                            str(target)], check=True)

    for name in ('aermod', 'aermap', 'aermet'):
        original = (source / name).resolve()
        if not original.is_file():
            raise RuntimeError(f'Eseguibile atteso non trovato: {original}')
        target = destination / name
        shutil.copy2(original, target)
        target.chmod(0o755)
        process(original, target, original)
    files = list(libdir.iterdir()) + [destination / x for x in ('aermod','aermap','aermet')]
    for path in files:
        for dep in deps(path):
            if not system(dep) and not dep.startswith('@loader_path/'):
                raise RuntimeError(f'Dipendenza esterna rimasta: {path}: {dep}')
        subprocess.run(['codesign', '--force', '--sign', '-', str(path)], check=True)
        subprocess.run(['codesign', '--verify', '--strict', str(path)], check=True)
    manifest = {str(p.relative_to(destination)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in files}
    (destination / 'SHA256.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (destination / 'LIBRERIE.txt').write_text(
        'Eseguibili compilati dai sorgenti EPA attraverso lo script PyAERMOD.\n'
        'Librerie runtime incluse; origine:\n' +
        '\n'.join(f'{v.name}: {k}' for k,v in copied.items()) + '\n\n'
        'GNU GCC e libgfortran: https://gcc.gnu.org/\n'
        'Licenze e Runtime Library Exception: https://gcc.gnu.org/onlinedocs/libstdc++/manual/license.html\n'
        'Conservare questo file e la diagnostica insieme al pacchetto.\n')


if __name__ == '__main__':
    if sys.platform != 'darwin':
        raise SystemExit('Questo script va eseguito sul runner macOS di GitHub.')
    source, destination = map(Path, sys.argv[1:3])
    if destination.exists():
        raise SystemExit(f'Cartella gia esistente: {destination}')
    destination.mkdir()
    bundle(source, destination, os.uname().machine)
