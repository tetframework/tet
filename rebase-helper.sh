#!/bin/bash
# Auto-resolve common conflicts during src-layout rebase
set -e

MAX_ITERATIONS=300
i=0

while [ $i -lt $MAX_ITERATIONS ]; do
    i=$((i + 1))

    if ! [ -d .git/rebase-merge ] && ! [ -d .git/rebase-apply ]; then
        echo "Rebase complete!"
        rm -f rebase-helper.sh
        exit 0
    fi

    current=$(cat .git/rebase-merge/msgnum 2>/dev/null || echo "?")
    total=$(cat .git/rebase-merge/end 2>/dev/null || echo "?")

    conflicts=$(git status --short | grep -E "^(UU|UA|DU|AU|AA)" || true)

    if [ -z "$conflicts" ]; then
        git add -A
        if ! GIT_EDITOR=true git rebase --continue 2>/dev/null; then
            continue
        fi
        continue
    fi

    echo "[$current/$total] Resolving..."

    resolved=true

    while IFS= read -r line; do
        status="${line:0:2}"
        file="${line:3}"

        case "$status" in
            "DU")
                # File deleted on HEAD, modified by commit (setup.py mostly)
                git rm -f "$file" 2>/dev/null || true
                ;;
            "UA"|"AU")
                git add "$file" 2>/dev/null || true
                ;;
            "AA")
                # Both added — take ours (branch)
                git checkout --theirs "$file" 2>/dev/null && git add "$file" || { echo "MANUAL: AA on $file"; resolved=false; }
                ;;
            "UU")
                markers=$(grep -c "<<<<<<" "$file" 2>/dev/null || echo 0)
                if [ "$markers" -eq 0 ]; then
                    git add "$file"
                    continue
                fi
                # Security files and tests: take theirs (branch version)
                # Non-security files: take ours (master version)
                case "$file" in
                    src/tet/security/*|tests/*|docs/authentication_apis*|docs/security_guide*|CHANGES.md|.github/*)
                        git checkout --theirs "$file" 2>/dev/null && git add "$file" || { echo "MANUAL: UU on $file"; resolved=false; }
                        ;;
                    *)
                        git checkout --ours "$file" 2>/dev/null && git add "$file" || { echo "MANUAL: UU on $file"; resolved=false; }
                        ;;
                esac
                ;;
            *)
                echo "MANUAL: $status on $file"
                resolved=false
                ;;
        esac
    done <<< "$conflicts"

    if [ "$resolved" = false ]; then
        echo "Stopping at step $current/$total — manual resolution needed"
        git status --short
        exit 1
    fi

    git add -A

    # Try continue; handle empty commits
    result=$(GIT_EDITOR=true git rebase --continue 2>&1) || {
        if echo "$result" | grep -q "No changes"; then
            echo "[$current/$total] Empty commit, skipping"
            git rebase --skip 2>/dev/null || true
        elif echo "$result" | grep -q "could not apply"; then
            # Next conflict, loop will handle it
            true
        else
            echo "Unexpected error: $result"
            exit 1
        fi
    }
done

echo "Hit max iterations"
exit 1
