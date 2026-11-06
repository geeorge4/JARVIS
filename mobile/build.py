"""Build and sign JARVIS Android with a local Android SDK and JDK."""
from pathlib import Path
import argparse
import os
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent


def run(*args):
    subprocess.run([str(arg) for arg in args], check=True)


def build(platform, tools, signing_key, output):
    signing_key.parent.mkdir(parents=True, exist_ok=True)
    if not signing_key.exists():
        run('keytool', '-genkeypair', '-keystore', signing_key, '-storepass', 'android',
            '-keypass', 'android', '-alias', 'androiddebugkey', '-keyalg', 'RSA',
            '-keysize', '2048', '-validity', '10000', '-dname', 'CN=JARVIS Android Preview')
    suffix = '.exe' if os.name == 'nt' else ''
    android_jar = platform / 'android.jar'
    with tempfile.TemporaryDirectory(prefix='jarvis-android-') as directory:
        work = Path(directory)
        classes = work / 'classes'
        classes.mkdir()
        resources = work / 'resources.zip'
        unsigned = work / 'unsigned.apk'
        aligned = work / 'aligned.apk'
        aapt2 = tools / ('aapt2' + suffix)
        run(aapt2, 'compile', '--dir', ROOT / 'res', '-o', resources)
        run(aapt2, 'link', '-I', android_jar, '--manifest', ROOT / 'AndroidManifest.xml',
            '-o', unsigned, resources)
        run('javac', '--release', '8', '-encoding', 'UTF-8', '-classpath', android_jar,
            '-d', classes, *sorted((ROOT / 'src').rglob('*.java')))
        run('java', '-cp', tools / 'lib' / 'd8.jar', 'com.android.tools.r8.D8',
            '--lib', android_jar, '--min-api', '23', '--output', work, *sorted(classes.rglob('*.class')))
        with zipfile.ZipFile(unsigned, 'a', zipfile.ZIP_DEFLATED) as apk:
            apk.write(work / 'classes.dex', 'classes.dex')
        run(tools / ('zipalign' + suffix), '-f', '4', unsigned, aligned)
        output.parent.mkdir(parents=True, exist_ok=True)
        signer = tools / 'lib' / 'apksigner.jar'
        run('java', '-jar', signer, 'sign', '--ks', signing_key, '--ks-key-alias', 'androiddebugkey',
            '--ks-pass', 'pass:android', '--key-pass', 'pass:android',
            '--v4-signing-enabled', 'false', '--out', output, aligned)
        run('java', '-jar', signer, 'verify', '--verbose', output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ('platform', 'tools', 'signing-key', 'output'):
        parser.add_argument('--' + option, type=Path, required=True)
    build(**vars(parser.parse_args()))

