Windows Tips
============
* git-cola is tested on msysgit
* Other git environments should work fine as long as `git`
  can be found in the $PATH.
* The provided `cola` shell script can be used to launch *git-cola*
  if you do not want to keep `python.exe` in your $PATH.
* If your python is installed in a location other than `/c/Python*/`
  then you can tell the `cola` script about it by setting the
  `cola.pythonlocation` git configuration variable.  e.g.:
 $ git config --global cola.pythonlocation "/c/Program Files/Python27/python.exe"
