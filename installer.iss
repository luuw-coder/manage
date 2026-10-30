#ifndef Suffix
#define Suffix ""
#endif
[Setup]
AppName=Manage Moho
AppVersion=0.1.0
DefaultDirName={autopf}\ManageMoho
DefaultGroupName=Manage Moho
OutputDir=dist-installer
OutputBaseFilename=ManageMoho_Setup{#Suffix}
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=lowest
SetupIconFile=assets\logo.ico
UninstallDisplayName=Manage Moho
UninstallDisplayIcon={app}\ManageMoho.exe

[Tasks]
Name: "desktopicon"; Description: "Tạo biểu tượng ngoài màn hình"

[Files]
Source: "dist\ManageMoho\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\Manage Moho"; Filename: "{app}\ManageMoho.exe"
Name: "{autodesktop}\Manage Moho"; Filename: "{app}\ManageMoho.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\ManageMoho.exe"; Description: "Mở Manage Moho"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Rác luôn bị xóa khi gỡ cài đặt
Type: filesandordirs; Name: "{userappdata}\ManageMoho\testdrag"
Type: files; Name: "{userappdata}\ManageMoho\keo.log"
Type: filesandordirs; Name: "{%PUBLIC|C:\Users\Public}\ManageMoho"
Type: filesandordirs; Name: "{app}"

[Code]
// Gỡ các script mà phần mềm đã chép vào Moho (tệp moho_script_paths.txt ghi lại nơi đã chép)
procedure RemoveRecordedScripts();
var
  Lines: TArrayOfString;
  I: Integer;
  P: String;
begin
  if LoadStringsFromFile(ExpandConstant('{userappdata}\ManageMoho\moho_script_paths.txt'), Lines) then
  begin
    for I := 0 to GetArrayLength(Lines) - 1 do
    begin
      P := Trim(Lines[I]);
      if P <> '' then
        DeleteFile(P);
    end;
  end;
end;

// Xóa bộ nhớ đệm trình duyệt AI (rác, tự tạo lại được) nhưng giữ phiên đăng nhập
procedure RemoveBrowserCaches();
var
  FR: TFindRec;
  Root, Acc: String;
begin
  Root := ExpandConstant('{userappdata}\ManageMoho\ai_profiles');
  if FindFirst(Root + '\*', FR) then
  begin
    try
      repeat
        if ((FR.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0) and (FR.Name <> '.') and (FR.Name <> '..') then
        begin
          Acc := Root + '\' + FR.Name;
          DelTree(Acc + '\cache', True, True, True);
          DelTree(Acc + '\Default\Cache', True, True, True);
          DelTree(Acc + '\Default\Code Cache', True, True, True);
          DelTree(Acc + '\Default\GPUCache', True, True, True);
          DelTree(Acc + '\GrShaderCache', True, True, True);
          DelTree(Acc + '\ShaderCache', True, True, True);
        end;
      until not FindNext(FR);
    finally
      FindClose(FR);
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    RemoveRecordedScripts();
    RemoveBrowserCaches();
    if not UninstallSilent then
    begin
      if MsgBox('Xóa luôn dữ liệu cá nhân của Manage Moho?' + #13#10 + #13#10 +
                'Gồm: kịch bản, danh sách mục, cài đặt, đăng nhập AI và các tệp âm thanh đã cắt ' +
                '(dự án Moho đang dùng chúng sẽ báo thiếu tệp).' + #13#10 + #13#10 +
                'Chọn "Không" để giữ lại, lần sau cài lại là dùng tiếp ngay. Rác tạm thì luôn được xóa.',
                mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
        DelTree(ExpandConstant('{userappdata}\ManageMoho'), True, True, True);
    end;
  end;
end;
