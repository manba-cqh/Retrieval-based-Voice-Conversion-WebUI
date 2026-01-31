; Inno Setup 安装脚本
; 用于打包娱音应用程序

#define AppName "娱音"
#define AppVersion "1.0"
#define AppPublisher "娱音"
#define AppURL ""
#define AppExeName "娱音.exe"
; 源目录路径（请根据实际情况修改）
#define SourceDir "F:\work\RVC20240604Nvidia"
; 输出目录路径（安装程序输出位置）
#define OutputDir "F:\work\RVC20240604Nvidia\dist"

[Setup]
; 应用程序基本信息
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
LicenseFile={#SourceDir}\LICENSE
OutputDir={#OutputDir}
OutputBaseFilename=娱音安装程序
SetupIconFile=
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
DiskSpanning=yes

[Languages]
; 方案1：如果找不到中文语言文件，注释掉下面这行，只使用英文
; Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
; 方案2：下载中文语言文件放到 Inno Setup 的 Languages 目录后，取消注释上面这行
; 下载地址：https://github.com/jrsoftware/issrc/raw/main/Files/Languages/ChineseSimplified.isl
; 或者：https://raw.githubusercontent.com/jrsoftware/issrc/main/Files/Languages/ChineseSimplified.isl
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1

[Files]
; 主程序
Source: "{#SourceDir}\娱音.exe"; DestDir: "{app}"; Flags: ignoreversion

; 批处理文件
Source: "{#SourceDir}\go-realtime-gui.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\go-web.bat"; DestDir: "{app}"; Flags: ignoreversion

; 根目录下的 Python 文件
Source: "{#SourceDir}\*.py"; DestDir: "{app}"; Flags: ignoreversion

; 配置文件
Source: "{#SourceDir}\config.ini"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\MIT协议暨相关引用库协议"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\README.md"; DestDir: "{app}"; Flags: ignoreversion

; FFmpeg 工具
Source: "{#SourceDir}\ffmpeg.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\ffprobe.exe"; DestDir: "{app}"; Flags: ignoreversion

; API 目录
Source: "{#SourceDir}\api\*"; DestDir: "{app}\api"; Flags: ignoreversion recursesubdirs

; Assets 目录（所有资源文件）
Source: "{#SourceDir}\assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs

; Configs 目录
Source: "{#SourceDir}\configs\*"; DestDir: "{app}\configs"; Flags: ignoreversion recursesubdirs

; Docs 目录
Source: "{#SourceDir}\docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs

; i18n 目录
Source: "{#SourceDir}\i18n\*"; DestDir: "{app}\i18n"; Flags: ignoreversion recursesubdirs

; Infer 目录
Source: "{#SourceDir}\infer\*"; DestDir: "{app}\infer"; Flags: ignoreversion recursesubdirs

; Pages 目录
Source: "{#SourceDir}\pages\*"; DestDir: "{app}\pages"; Flags: ignoreversion recursesubdirs

; Res 目录（资源文件）
Source: "{#SourceDir}\res\*"; DestDir: "{app}\res"; Flags: ignoreversion recursesubdirs

; Runtime 目录（Python 运行时环境，完整包含）
Source: "{#SourceDir}\runtime\*"; DestDir: "{app}\runtime"; Flags: ignoreversion recursesubdirs

; Tools 目录
Source: "{#SourceDir}\tools\*"; DestDir: "{app}\tools"; Flags: ignoreversion recursesubdirs

; Utils 目录
Source: "{#SourceDir}\utils\*"; DestDir: "{app}\utils"; Flags: ignoreversion recursesubdirs

; Logs 目录（可能为空，但保留结构）
Source: "{#SourceDir}\logs\*"; DestDir: "{app}\logs"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// 初始化安装程序
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

