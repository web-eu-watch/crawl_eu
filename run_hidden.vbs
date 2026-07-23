Set WshShell = CreateObject("WScript.Shell")
' 0 : 창을 완전히 숨김(Hide) / False : 비동기 실행
WshShell.Run """" & WshShell.CurrentDirectory & "\eu.bat""", 0, False