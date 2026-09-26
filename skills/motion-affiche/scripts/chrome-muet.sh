#!/bin/sh
# Chrome pour render.py, sorties vers /dev/null : sinon son chrome_crashpad_handler, détaché, hérite de la sortie
# d'erreur reliée au pilote Playwright, et nav.close() attend sa fermeture sans fin (rendus figés après la dernière
# image, 2 à 4 navigateurs sur 4, 25/09/26).
exec "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" "$@" >/dev/null 2>&1
