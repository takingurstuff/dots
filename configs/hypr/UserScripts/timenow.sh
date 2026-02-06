#!/bin/bash

# Lazy Ass Script to get current datetime because i cant be bothered with yuck

while true; do
  printf -v year '%(%Y)T' -1
  printf -v month '%(%B)T' -1
  printf -v day '%(%d)T' -1
  printf -v hour '%(%H)T' -1
  printf -v minute '%(%M)T' -1
  printf -v second '%(%S)T' -1
  printf -v weekday '%(%A)T' -1

  json_datetime="{\"year\": \"$year\", \"month\": \"$month\", \"day\": \"$day\", \"hour\": \"$hour\", \"minute\": \"$minute\", \"second\": \"$second\", \"weekday\": \"$weekday\"}"

  echo "$json_datetime"
  sleep 0.5
done