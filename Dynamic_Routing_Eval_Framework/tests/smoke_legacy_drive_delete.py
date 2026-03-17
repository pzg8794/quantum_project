import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from daqr.config.local_backup_manager import LocalBackupManager

CONFIG_DIR = ROOT / 'daqr' / 'config'
DATE = 'day_20990317'
FILENAME = 'SmokeLegacyRunner.pkl'
COMPONENT = 'framework_state'

mgr = LocalBackupManager(DATE, CONFIG_DIR, verbose=True)
local_path = ROOT / 'daqr' / 'config' / 'framework_state' / DATE / FILENAME
restored_path = ROOT / 'daqr' / 'config' / 'quantum_data_lake' / 'framework_state' / DATE / FILENAME

result = mgr.delete_from_drive(COMPONENT, FILENAME)
print(json.dumps({
    'delete_result': result,
    'local_exists_after_delete': local_path.exists(),
    'downloaded_exists_after_delete': restored_path.exists(),
    'local_path': str(local_path),
    'downloaded_path': str(restored_path),
}, indent=2))
