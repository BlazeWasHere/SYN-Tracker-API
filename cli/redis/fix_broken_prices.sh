#!/usr/bin/env bash

for key in $(redis-cli KEYS '*'); do
    value=$(redis-cli GET $key);

    if [ "$value" = "0" ]; then
        echo $key;
        redis-cli DEL $key;
    fi
done
