import json
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from daqr.config.local_backup_manager import LocalBackupManager

CONFIG_DIR = ROOT / 'daqr' / 'config' / 'quantum_data_lake'
DATE = 'day_20990317'
FILENAME = 'SmokeLegacyRunner.pkl'
COMPONENT = 'framework_state'

mgr = LocalBackupManager(DATE, CONFIG_DIR, verbose=True)
local_path = Path(mgr.save_file(COMPONENT, FILENAME, {'smoke': True, 'ts': time.time()}))
restored = mgr._download_file_from_drive(DATE, COMPONENT, FILENAME)
restored_path = Path(restored) if restored else None
print(json.dumps({
    'local_path': str(local_path),
    'local_exists': local_path.exists(),
    'downloaded_path': str(restored_path) if restored_path else None,
    'downloaded_exists': restored_path.exists() if restored_path else False,
}, indent=2))
