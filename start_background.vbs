' Запускает парсер в фоне без консоли на Windows
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd /c ""cd /d """"" & Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\")-1) & """""" & """" & """.venv\Scripts\activate.bat"""" & """" & """ && python main.py""""""", 0, False
Set WshShell = Nothing
