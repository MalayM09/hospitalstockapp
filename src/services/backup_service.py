"""
Backup Service - Automatic database backup on each modification
"""
import shutil
from pathlib import Path
from datetime import datetime
import os


class BackupService:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.backup_dir = db_path.parent / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.max_backups = 10  # Keep last 10 backups
    
    def create_backup(self):
        """Create a timestamped backup of the database."""
        if not self.db_path.exists():
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"hospital_backup_{timestamp}.db"
        backup_path = self.backup_dir / backup_name
        
        try:
            shutil.copy2(self.db_path, backup_path)
            self._cleanup_old_backups()
            return backup_path
        except Exception as e:
            print(f"Backup failed: {e}")
            return None
    
    def _cleanup_old_backups(self):
        """Keep only the most recent backups."""
        backups = sorted(
            self.backup_dir.glob("hospital_backup_*.db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        # Remove old backups beyond max_backups
        for old_backup in backups[self.max_backups:]:
            try:
                old_backup.unlink()
            except Exception:
                pass
    
    def get_backups(self):
        """Get list of available backups."""
        backups = sorted(
            self.backup_dir.glob("hospital_backup_*.db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        return backups
    
    def restore_backup(self, backup_path: Path):
        """Restore database from backup."""
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_path}")
        
        # Create a backup of current before restore
        self.create_backup()
        
        # Restore
        shutil.copy2(backup_path, self.db_path)
        return True
