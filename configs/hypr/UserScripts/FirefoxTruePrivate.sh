#!/bin/sh

# 1. Create a temporary directory for the profile
PROFILEDIR=$(mktemp -d /"$XDG_RUNTIME_DIR"/tmp-ff-profile.XXXXXX)

# 2. Run Firefox using the temporary profile directory
# -no-remote ensures a separate Firefox process
firefox -profile "$PROFILEDIR" -no-remote -new-instance

# 3. Once Firefox is closed, remove the temporary directory and all its contents
rm -rf "$PROFILEDIR"
