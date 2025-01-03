import PyInstaller.__main__
import shutil
from pathlib import Path

# Clean previous builds
for path in ['build', 'dist']:
    if Path(path).exists():
        shutil.rmtree(path)

PyInstaller.__main__.run([
    'chatsnap.spec',
    '--clean',
    '--noconfirm'
])

# Copy additional files to dist folder
shutil.copy('README.md', 'dist/README.md')
print("Build complete! Check the 'dist' folder for the executable.") 