#define APP_NAME     'git-cola'
#define APP_LONGNAME 'git-cola - The highly caffeinated git GUI'
#define APP_VERSION  '%APPVERSION%'
#define APP_URL      'http://git-cola.github.io/'

[Setup]
; Compiler-related
InternalCompressLevel=max
OutputBaseFilename={#emit APP_NAME+'-'+APP_VERSION}
OutputDir=%OUTPUTDIR%
SolidCompression=yes

; Installer-related
AllowNoIcons=yes
AppName={#emit APP_LONGNAME}
AppPublisherURL={#emit APP_URL}
AppVersion={#emit APP_VERSION}
AppVerName={#emit APP_LONGNAME+' '+APP_VERSION}
ChangesEnvironment=yes
DefaultDirName={pf}\{#emit APP_NAME}
DefaultGroupName={#emit APP_LONGNAME}
DisableReadyPage=yes
InfoBeforeFile=etc\gpl-2.0.rtf
PrivilegesRequired=none
UninstallDisplayIcon=etc\git.ico

; Cosmetic
SetupIconFile=etc\git.ico
WizardSmallImageFile=etc\git.bmp

[Tasks]
Name: quicklaunchicon; Description: "Create a &Quick Launch icon"; GroupDescription: "Additional icons:"; Flags: checkedonce
Name: desktopicon; Description: "Create a &Desktop icon"; GroupDescription: "Additional icons:"; Flags: checkedonce
Name: guiextension; Description: "Add ""Git &Cola Here"""; GroupDescription: "Windows Explorer integration:"; Flags: checkedonce

[Files]
Source: "*"; DestDir: "{app}"; Excludes: "\*.bmp, \install.*, \tmp.*, \bin\*install*"; Flags: recursesubdirs
Source: "etc\ReleaseNotes.txt"; DestDir: "{app}\etc"; Flags: isreadme

[Icons]
Name: "{group}\git-cola"; Filename: "{code:GetPythonExe}"; Parameters: """{app}\bin\git-cola.pyw"" --prompt --git-path ""{code:GetGitExe}"""; WorkingDir: "%USERPROFILE%"; IconFilename: "{app}\etc\git.ico"
Name: "{group}\git-dag"; Filename: "{code:GetPythonExe}"; Parameters: """{app}\bin\git-dag.pyw"" --prompt --git-path ""{code:GetGitExe}"""; WorkingDir: "%USERPROFILE%"; IconFilename: "{app}\etc\git.ico"
Name: "{group}\git-cola Homepage"; Filename: "{#emit APP_URL}"; WorkingDir: "%USERPROFILE%";
Name: "{group}\Release Notes"; Filename: "{app}\etc\ReleaseNotes.txt"; WorkingDir: "%USERPROFILE%";
Name: "{group}\License"; Filename: "{app}\etc\gpl-2.0.rtf"; WorkingDir: "%USERPROFILE%";
Name: "{group}\Uninstall git-cola"; Filename: "{uninstallexe}"
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\git-cola"; Filename: "{code:GetPythonExe}"; Parameters: """{app}\bin\git-cola.pyw"" --prompt --git-path ""{code:GetGitExe}"""; WorkingDir: "%USERPROFILE%"; IconFilename: "{app}\etc\git.ico"; Tasks: quicklaunchicon
Name: "{code:GetShellFolder|desktop}\git-cola"; Filename: "{code:GetPythonExe}"; Parameters: """{app}\bin\git-cola.pyw"" --prompt --git-path ""{code:GetGitExe}"""; WorkingDir: "%USERPROFILE%"; IconFilename: "{app}\etc\git.ico"; Tasks: desktopicon
Name: "{code:GetShellFolder|desktop}\git-dag"; Filename: "{code:GetPythonExe}"; Parameters: """{app}\bin\git-dag.pyw"" --prompt --git-path ""{code:GetGitExe}"""; WorkingDir: "%USERPROFILE%"; IconFilename: "{app}\etc\git.ico"; Tasks: desktopicon

[Messages]
BeveledLabel={#emit APP_URL}
SetupAppTitle={#emit APP_NAME} Setup
SetupWindowTitle={#emit APP_NAME} Setup

[UninstallDelete]
Type: files; Name: "{app}\bin\*"
Type: files; Name: "{app}\etc\*"
Type: files; Name: "{app}\share\git-cola\bin\*"
Type: files; Name: "{app}\share\git-cola\icons\*"
Type: files; Name: "{app}\share\git-cola\lib\cola\*"
Type: files; Name: "{app}\share\git-cola\lib\cola\classic\*"
Type: files; Name: "{app}\share\git-cola\lib\cola\dag\*"
Type: files; Name: "{app}\share\git-cola\lib\cola\main\*"
Type: files; Name: "{app}\share\git-cola\lib\cola\merge\*"
Type: files; Name: "{app}\share\git-cola\lib\cola\models\*"
Type: files; Name: "{app}\share\git-cola\lib\cola\prefs\*"
Type: files; Name: "{app}\share\git-cola\lib\cola\stash\*"
Type: files; Name: "{app}\share\git-cola\lib\cola\widgets\*"
Type: dirifempty; Name: "{app}\share\git-cola\lib\cola\classic"
Type: dirifempty; Name: "{app}\share\git-cola\lib\cola\dag"
Type: dirifempty; Name: "{app}\share\git-cola\lib\cola\main"
Type: dirifempty; Name: "{app}\share\git-cola\lib\cola\merge"
Type: dirifempty; Name: "{app}\share\git-cola\lib\cola\models"
Type: dirifempty; Name: "{app}\share\git-cola\lib\cola\prefs"
Type: dirifempty; Name: "{app}\share\git-cola\lib\cola\stash"
Type: dirifempty; Name: "{app}\share\git-cola\lib\cola\widgets"
Type: dirifempty; Name: "{app}\share\git-cola\lib\cola"
Type: dirifempty; Name: "{app}\share\git-cola\lib"
Type: dirifempty; Name: "{app}\share\git-cola\icons"
Type: dirifempty; Name: "{app}\share\git-cola\bin"
Type: dirifempty; Name: "{app}\etc"
Type: dirifempty; Name: "{app}\bin"

[Code]
{
    Helper methods
}

var
    PythonPage:TWizardPage;
    GitPage:TWizardPage;
    EdtPython:TEdit;
    EdtGit:TEdit;

function GetEnvStrings(VarName:string;AllUsers:Boolean):TArrayOfString;
var
    Path:string;
    i:Longint;
    p:Integer;
begin
    Path:='';

    // See http://www.jrsoftware.org/isfaq.php#env
    if AllUsers then begin
        // We ignore errors here. The resulting array of strings will be empty.
        RegQueryStringValue(HKEY_LOCAL_MACHINE,'SYSTEM\CurrentControlSet\Control\Session Manager\Environment',VarName,Path);
    end else begin
        // We ignore errors here. The resulting array of strings will be empty.
        RegQueryStringValue(HKEY_CURRENT_USER,'Environment',VarName,Path);
    end;

    // Make sure we have at least one semicolon.
    Path:=Path+';';

    // Split the directories in PATH into an array of strings.
    i:=0;
    SetArrayLength(Result,0);

    p:=Pos(';',Path);
    while p>0 do begin
        SetArrayLength(Result,i+1);
        if p>1 then begin
            Result[i]:=Copy(Path,1,p-1);
            i:=i+1;
        end;
        Path:=Copy(Path,p+1,Length(Path));
        p:=Pos(';',Path);
    end;
end;

function SetEnvStrings(VarName:string;AllUsers,DeleteIfEmpty:Boolean;DirStrings:TArrayOfString):Boolean;
var
    Path,KeyName:string;
    i:Longint;
begin
    // Merge all non-empty directory strings into a PATH variable.
    Path:='';
    for i:=0 to GetArrayLength(DirStrings)-1 do begin
        if Length(DirStrings[i])>0 then begin
            if Length(Path)>0 then begin
                Path:=Path+';'+DirStrings[i];
            end else begin
                Path:=DirStrings[i];
            end;
        end;
    end;

    // See http://www.jrsoftware.org/isfaq.php#env
    if AllUsers then begin
        KeyName:='SYSTEM\CurrentControlSet\Control\Session Manager\Environment';
        if DeleteIfEmpty and (Length(Path)=0) then begin
            Result:=(not RegValueExists(HKEY_LOCAL_MACHINE,KeyName,VarName))
                      or RegDeleteValue(HKEY_LOCAL_MACHINE,KeyName,VarName);
        end else begin
            Result:=RegWriteStringValue(HKEY_LOCAL_MACHINE,KeyName,VarName,Path);
        end;
    end else begin
        KeyName:='Environment';
        if DeleteIfEmpty and (Length(Path)=0) then begin
            Result:=(not RegValueExists(HKEY_CURRENT_USER,KeyName,VarName))
                      or RegDeleteValue(HKEY_CURRENT_USER,KeyName,VarName);
        end else begin
            Result:=RegWriteStringValue(HKEY_CURRENT_USER,KeyName,VarName,Path);
        end;
    end;
end;


procedure BrowseForPythonFolder(Sender:TObject);
var
    Path:string;
begin
    Path:=GetPreviousData('PythonPath', 'C:\Python27');
    EdtPython.Text:=Path;
    Path:=ExtractFilePath(EdtPython.Text);
    BrowseForFolder('Please select the Python folder:',Path,False);
    Path:=Path+'\pythonw.exe';
    if FileExists(Path) then begin
        EdtPython.Text:=Path;
    end else begin
        MsgBox('Please enter a valid path to pythonw.exe.',mbError,MB_OK);
    end;
end;

function GetPythonExe(Param: String): String;
begin
    Result:=EdtPython.Text;
end;

procedure BrowseForGitFolder(Sender:TObject);
var
    Path:string;
    OldPath:string;
begin
    Path:=GetPreviousData('GitPath', 'C:\Program Files\Git');
    EdtGit.Text:=Path;
    Path:=ExtractFilePath(EdtGit.Text);
    BrowseForFolder('Please select the Git folder:',Path,False);
    OldPath:=Path;

    {
        Check for both $DIR\git.exe and $DIR\bin\git.exe
    }

    Path:=OldPath+'\bin\git.exe';
    if FileExists(Path) then begin
        EdtGit.Text:=Path;
        Exit; 
    end;

    Path:=OldPath+'\git.exe';
    if FileExists(Path) then begin
        EdtGit.Text:=Path;
    end else begin
        MsgBox('Please enter a valid path to git.exe.',mbError,MB_OK);
    end;
end;


function GetGitExe(Param: String): String;
begin
    Result:=EdtGit.Text;
end;

procedure RegisterPreviousData(PreviousDataKey:Integer);
var
    Path:string;
begin
    Path:=ExtractFilePath(EdtPython.Text);
    SetPreviousData(PreviousDataKey, 'PythonPath', Path);

    Path:=ExtractFilePath(ExtractFilePath(EdtGit.Text));
    SetPreviousData(PreviousDataKey, 'GitPath', Path);
end;

{
    Installer code
}


procedure InitializeWizard;
var
    BtnPython:TButton;
    BtnGit:TButton;
    LblPython:TLabel;
    LblGit:TLabel;
begin
    // Create a custom page for finding Python
    PythonPage:=CreateCustomPage(
        wpSelectTasks,
        'Setup Python',
        'Where is your Python folder?'
    );

    LblPython:=TLabel.Create(PythonPage);
    with LblPython do begin
        Parent:=PythonPage.Surface;
        Caption:= 'Please provide the path to pythonw.exe.';
        Left:=ScaleX(28);
        Top:=ScaleY(100);
        Width:=ScaleX(316);
        Height:=ScaleY(39);
    end;

    EdtPython:=TEdit.Create(PythonPage);
    with EdtPython do begin
        Parent:=PythonPage.Surface;
        Text:=GetPreviousData('PythonPath', 'C:\Python26');
        Text:=Text+'pythonw.exe';
        if not FileExists(Text) then begin
            Text:='';
        end;
        Left:=ScaleX(28);
        Top:=ScaleY(148);
        Width:=ScaleX(316);
        Height:=ScaleY(13);
    end;

    BtnPython:=TButton.Create(PythonPage);
    with BtnPython do begin
        Parent:=PythonPage.Surface;
        Caption:='...';
        OnClick:=@BrowseForPythonFolder;
        Left:=ScaleX(348);
        Top:=ScaleY(148);
        Width:=ScaleX(21);
        Height:=ScaleY(21);
    end;

    // Create a custom page for finding Git
    GitPage:=CreateCustomPage(
        wpSelectTasks,
        'Setup Git',
        'Where is your Git folder?'
    );

    LblGit:=TLabel.Create(GitPage);
    with LblGit do begin
        Parent:=GitPage.Surface;
        Caption:= 'Please provide the path to git.exe.';
        Left:=ScaleX(28);
        Top:=ScaleY(100);
        Width:=ScaleX(316);
        Height:=ScaleY(39);
    end;

    EdtGit:=TEdit.Create(GitPage);
    with EdtGit do begin
        Parent:=GitPage.Surface;
        Text:=GetPreviousData('GitPath', 'C:\Program Files\Git');
        Text:=Text+'git.exe';
        if not FileExists(Text) then begin
            Text:='';
        end;
        Left:=ScaleX(28);
        Top:=ScaleY(148);
        Width:=ScaleX(316);
        Height:=ScaleY(13);
    end;

    BtnGit:=TButton.Create(GitPage);
    with BtnGit do begin
        Parent:=GitPage.Surface;
        Caption:='...';
        OnClick:=@BrowseForGitFolder;
        Left:=ScaleX(348);
        Top:=ScaleY(148);
        Width:=ScaleX(21);
        Height:=ScaleY(21);
    end;
end;

function NextButtonClick(CurPageID:Integer):Boolean;
begin
    if CurPageID = PythonPage.ID then begin
        Result:=FileExists(EdtPython.Text);

        if not Result then begin
            MsgBox('Please enter a valid path to pythonw.exe.',mbError,MB_OK);
        end;
        Exit;
    end;

    if CurPageID = GitPage.ID then begin
        Result:=FileExists(EdtGit.Text);

        if not Result then begin
            MsgBox('Please enter a valid path to git.exe.',mbError,MB_OK);
        end;
        Exit;
    end;

    Result:=True;
end;

procedure CurStepChanged(CurStep:TSetupStep);
var
    AppDir,BinDir,Msg:string;
    EnvPath:TArrayOfString;
    i:Longint;
    RootKey:Integer;
begin
    if CurStep<>ssPostInstall then begin
        Exit;
    end;

    AppDir:=ExpandConstant('{app}');
    BinDir:=ExpandConstant('{app}\bin');

    {
        Modify the environment

        This must happen no later than ssPostInstall to make
        "ChangesEnvironment=yes" not happend before the change!
    }

    // Get the current user's directories in PATH.
    EnvPath:=GetEnvStrings('PATH',IsAdminLoggedOn);

    // First, remove the installation directory from PATH in any case.
    for i:=0 to GetArrayLength(EnvPath)-1 do begin
        if Pos(AppDir,EnvPath[i])=1 then begin
            EnvPath[i]:='';
        end;
    end;

    // Modify the PATH variable as requested by the user.
    i:=GetArrayLength(EnvPath);
    SetArrayLength(EnvPath,i+1);

    // Add \bin to the path
    EnvPath[i]:=BinDir

    // Set the current user's PATH directories.
    if not SetEnvStrings('PATH',IsAdminLoggedOn,True,EnvPath) then begin
        Msg:='Line {#emit __LINE__}: Unable to set the PATH environment variable.';
        MsgBox(Msg,mbError,MB_OK);
        Log(Msg);
        // This is not a critical error, the user can probably fix it manually,
        // so we continue.
    end;

    {
        Create the Windows Explorer shell extensions
    }

    if IsAdminLoggedOn then begin
        RootKey:=HKEY_LOCAL_MACHINE;
    end else begin
        RootKey:=HKEY_CURRENT_USER;
    end;

    if IsTaskSelected('guiextension') then begin
        if (not RegWriteStringValue(RootKey,'SOFTWARE\Classes\Directory\shell\git_cola','','Git &Cola Here'))
        or (not RegWriteStringValue(RootKey,'SOFTWARE\Classes\Directory\shell\git_cola\command','','"'+EdtPython.Text+'" "'+AppDir+'\bin\git-cola.pyw" "--repo" "%1" "--git-path" "'+EdtGit.Text+'"')) then begin
            Msg:='Line {#emit __LINE__}: Unable to create "Git Cola Here" shell extension.';
            MsgBox(Msg,mbError,MB_OK);
            Log(Msg);
            // This is not a critical error, the user can probably fix it manually,
            // so we continue.
        end;
    end;
end;

{
    Uninstaller code
}

function InitializeUninstall:Boolean;
begin
    Result:=True;
end;

procedure CurUninstallStepChanged(CurUninstallStep:TUninstallStep);
var
    AppDir,Command,Msg:string;
    EnvPath:TArrayOfString;
    i:Longint;
    RootKey:Integer;
begin
    if CurUninstallStep<>usUninstall then begin
        Exit;
    end;

    {
        Modify the environment

        This must happen no later than usUninstall to make
        "ChangesEnvironment=yes" not happend before the change!
    }

    AppDir:=ExpandConstant('{app}');
    Command:=AppDir+'\setup.ini';

    // Get the current user's directories in PATH.
    EnvPath:=GetEnvStrings('PATH',IsAdminLoggedOn);

    // Remove the installation directory from PATH in any case, even if it
    // was not added by the installer.
    for i:=0 to GetArrayLength(EnvPath)-1 do begin
        if Pos(AppDir,EnvPath[i])=1 then begin
            EnvPath[i]:='';
        end;
    end;

    // Reset the current user's directories in PATH.
    if not SetEnvStrings('PATH',IsAdminLoggedOn,True,EnvPath) then begin
        Msg:='Line {#emit __LINE__}: Unable to revert any possible changes to PATH.';
        MsgBox(Msg,mbError,MB_OK);
        Log(Msg);
        // This is not a critical error, the user can probably fix it manually,
        // so we continue.
    end;

    if (FileExists(Command) and (not DeleteFile(Command))) then begin
        Msg:='Line {#emit __LINE__}: Unable to delete file "'+Command+'".';
        MsgBox(Msg,mbError,MB_OK);
        Log(Msg);
        // This is not a critical error, the user can probably fix it manually,
        // so we continue.
    end;

    {
        Delete the Windows Explorer shell extensions
    }

    if IsAdminLoggedOn then begin
        RootKey:=HKEY_LOCAL_MACHINE;
    end else begin
        RootKey:=HKEY_CURRENT_USER;
    end;

    Command:='';
    RegQueryStringValue(RootKey,'SOFTWARE\Classes\Directory\shell\git_cola\command','',Command);
    if Pos(AppDir,Command)>0 then begin
        if not RegDeleteKeyIncludingSubkeys(RootKey,'SOFTWARE\Classes\Directory\shell\git_cola') then begin
            Msg:='Line {#emit __LINE__}: Unable to remove "Git Cola Here" shell extension.';
            MsgBox(Msg,mbError,MB_OK);
            Log(Msg);
            // This is not a critical error, the user can probably fix it manually,
            // so we continue.
        end;
    end;
end;

function GetShellFolder(Param:string):string;
begin
    if IsAdminLoggedOn then begin
        Param:='{common'+Param+'}';
    end else begin
        Param:='{user'+Param+'}';
    end;
    Result:=ExpandConstant(Param);
end;
