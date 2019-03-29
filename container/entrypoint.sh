#!/usr/bin/env bash

if [[ $# -lt 1 ]] || [[ "$1" == "-"* ]]; then
  if [ ! -z "$CONF_FILE" ]; then
    PARAMS="--conf-file $CONF_FILE"
  fi

  if [ ! -z "$OSCRC_FILE" ]; then
    # osc needs to 'chmod 0600' the oscrc file
    # but this is an issue when mounting the file
    # in a container
    OSCRC_FILE_NEW="/tmp/$(basename $OSCRC_FILE).new"
    cp -v "$OSCRC_FILE" "$OSCRC_FILE_NEW"
    PARAMS="$PARAMS --oscrc-file $OSCRC_FILE_NEW"
  fi
  
  if [ "$SHOW_OSC_COMMANDS" = "true" ]; then
    PARAMS="$PARAMS --show-osc-commands"
  fi

  echo "/usr/bin/python3 /app/prpmguy.py $PARAMS $@"
  exec /usr/bin/python3 /app/prpmguy.py $PARAMS $@
fi

exec "$@"
