#define MyAppName "Monn Studio"
#define MyAppVersion "1.5.0"
#define MyAppPublisher "AmirHosseinNzafat"
#define MyAppExeName "MonnStudio.exe"

[Setup]
AppId={{C2A4C86D-77B5-4A9A-9E3E-1A4D0B2A7D43}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Monn Studio
DefaultGroupName=Monn Studio
OutputDir=..\..\dist\installer
OutputBaseFilename=MonnStudio-Setup-{#MyAppVersion}
SetupIconFile=..\..\assets\monn-studio.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesInstallIn64BitMode=x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "..\..\dist\MonnStudio.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Monn Studio"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Monn Studio"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "ایجاد میانبر روی دسکتاپ"; GroupDescription: "میانبرها:"
