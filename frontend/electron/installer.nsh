!macro customInstall
  nsExec::Exec '"$INSTDIR\resources\jon-backend\jon-backend.exe" terminal-einrichten'
!macroend

!macro customUnInstall
  ${ifNot} ${isUpdated}
    Delete "$LOCALAPPDATA\Jon\bin\jon.cmd"
  ${endIf}
!macroend
