from pathlib import Path
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
class DistributionTests(unittest.TestCase):
    def test_package_excludes_private_assets(self):
        with zipfile.ZipFile(ROOT/'dist'/'jarvis-app.zip') as archive:
            names=archive.namelist()
            self.assertIn('LICENSE',names)
            self.assertIn('jarvis_ui.py',names)
            for name in names:
                self.assertFalse(name.lower().endswith(('.mp3','.m4a','.wav','.log')))
                self.assertFalse(name.startswith(('Python/','models/','round-drops/')))
                self.assertNotIn(name,('settings.json','activation.json','memory.json','cs2-token.txt'))
            self.assertIn('geeorge42_alt01 on ROBLOX',archive.read('LICENSE').decode())
    def test_settings_save_preserves_other_keys(self):
        spec=importlib.util.spec_from_file_location('public_product',ROOT/'product.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            module.PREFS=Path(temp)/'settings.json'
            original={'setup_done':True,'seen_version':'older','voice_engine':'xtts','unknown_future':123}
            module.PREFS.write_text(json.dumps(original),encoding='utf-8')
            module.save(hotkey='Ctrl+J')
            for key,value in original.items():self.assertEqual(module.load()[key],value)
    @unittest.skipUnless(os.name=='nt','Windows executable')
    def test_native_installer_preserves_data(self):
        executable=str(ROOT/'dist'/'InstallUpdates.exe')
        self.assertEqual(subprocess.run([executable,'--verify']).returncode,0)
        with tempfile.TemporaryDirectory(prefix='jarvis-install-test-') as temp:
            root=Path(temp)
            for relative in ('settings.json','round-drops/private.wav','models/private.bin','Python/private.txt'):
                file=root/relative;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(b'KEEP ME')
            result=subprocess.run([executable,'--test-install',temp])
            self.assertEqual(result.returncode,0)
            for relative in ('settings.json','round-drops/private.wav','models/private.bin','Python/private.txt'):
                self.assertEqual((root/relative).read_bytes(),b'KEEP ME')
            self.assertTrue((root/'JARVIS.exe').is_file())
            self.assertEqual((root/'README.md').read_bytes(),(root/'README.txt').read_bytes())

if __name__=='__main__':unittest.main()
