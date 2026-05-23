if status is-interactive
# Commands to run in interactive sessions can go here
8fetch
end

function fish_greeting
    set hour (date "+%H")
    set current_time (date "+%H:%M")

    if test $hour -lt 12
        set greeting "morning"
    else if test $hour -lt 18
        set greeting "afternoon"
    else
        set greeting "evening"
    end

    echo "  Good $greeting, $USER! It is currently $current_time."
end

function fish_prompt
    set -l path (prompt_pwd)

    if test "$path" = "~"
        set path "/home"
    end

    echo -n " $path    "
end
