#!/bin/bash
# Auto-resolve common conflicts during src-layout rebase
# Stops on conflicts it can't handle

set -e

MAX_ITERATIONS=200
i=0

while [ $i -lt $MAX_ITERATIONS ]; do
    i=$((i + 1))

    # Check if rebase is still in progress
    if ! [ -d .git/rebase-merge ] && ! [ -d .git/rebase-apply ]; then
        echo "Rebase complete!"
        exit 0
    fi

    # Get current step info
    if [ -d .git/rebase-merge ]; then
        current=$(cat .git/rebase-merge/msgnum 2>/dev/null || echo "?")
        total=$(cat .git/rebase-merge/end 2>/dev/null || echo "?")
    else
        current="?"
        total="?"
    fi

    # Get conflicting files
    conflicts=$(git status --short | grep -E "^(UU|UA|DU|AU|AA)" || true)

    if [ -z "$conflicts" ]; then
        # No conflicts, just unmerged paths — add all and continue
        git add -A
        if ! GIT_EDITOR=true git rebase --continue 2>/dev/null; then
            continue
        fi
        continue
    fi

    echo "[$current/$total] Conflicts: $conflicts"

    resolved=true

    while IFS= read -r line; do
        status="${line:0:2}"
        file="${line:3}"

        case "$status" in
            "DU")
                # File deleted on HEAD (master), modified by our commit
                # setup.py was deleted in src-layout migration
                if [ "$file" = "setup.py" ]; then
                    git rm -f setup.py 2>/dev/null || true
                else
                    echo "MANUAL: DU conflict on $file"
                    resolved=false
                fi
                ;;
            "UA")
                # File added by our commit in a renamed directory
                # Git already suggests the right location, just add it
                git add "$file" 2>/dev/null || true
                ;;
            "AU")
                # Added on HEAD, unmerged by us
                git add "$file" 2>/dev/null || true
                ;;
            "AA")
                # Both added — take ours (the branch version)
                if git checkout --theirs "$file" 2>/dev/null; then
                    git add "$file"
                else
                    echo "MANUAL: AA conflict on $file"
                    resolved=false
                fi
                ;;
            "UU")
                # Both modified — check if it's a simple case
                markers=$(grep -c "<<<<<<" "$file" 2>/dev/null || echo 0)
                if [ "$markers" -eq 0 ]; then
                    git add "$file"
                else
                    # Try taking ours for known files
                    case "$file" in
                        tests/conftest.py|tests/*)
                            git checkout --theirs "$file" 2>/dev/null && git add "$file" || { echo "MANUAL: UU on $file"; resolved=false; }
                            ;;
                        *)
                            echo "MANUAL: UU conflict ($markers markers) on $file"
                            resolved=false
                            ;;
                    esac
                fi
                ;;
            *)
                echo "MANUAL: Unknown status $status on $file"
                resolved=false
                ;;
        esac
    done <<< "$conflicts"

    if [ "$resolved" = false ]; then
        echo "Stopping — manual resolution needed at step $current/$total"
        exit 1
    fi

    git add -A
    if ! GIT_EDITOR=true git rebase --continue 2>/dev/null; then
        # rebase --continue might fail if there are no changes (empty commit)
        # Try skip in that case
        if git diff --cached --quiet 2>/dev/null; then
            echo "[$current/$total] Empty commit, skipping"
            git rebase --skip 2>/dev/null || true
        fi
    fi
done

echo "Hit max iterations ($MAX_ITERATIONS)"
exit 1
