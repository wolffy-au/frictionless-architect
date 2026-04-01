#!/bin/sh

sudo apt-get update
sudo apt-get install dos2unix

dos2unix `find . -type f -name "*.sh"`
chmod +x `find . -type f -name "*.sh"`

git config --global user.name "Stephan Borg"
git config --global user.email "wolffborg1@gmail.com"
