Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd /c locallm stop server", 0, False
