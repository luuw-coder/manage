[Setup]
AppName=Manage Moho
AppVersion=0.1.0
DefaultDirName={autopf}\ManageMoho
DefaultGroupName=Manage Moho
OutputDir=dist-installer
OutputBaseFilename=ManageMoho_Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
UninstallDisplayName=Manage Moho

[Tasks]
Name: "desktopicon"; Description: "Tạo biểu tượng ngoài màn hình"

[Files]
Source: "dist\ManageMoho\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\Manage Moho"; Filename: "{app}\ManageMoho.exe"
Name: "{autodesktop}\Manage Moho"; Filename: "{app}\ManageMoho.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\ManageMoho.exe"; Description: "Mở Manage Moho"; Flags: nowait postinstall skipifsilent
