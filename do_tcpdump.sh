#!/usr/bin/env sh
set -e

INTERFACE="${1:-loopback}"

sudo rm -rf $INTERFACE.pcap || true
echo "Starting tcpdump on $INTERFACE"
sudo tcpdump -i $INTERFACE -U -w $INTERFACE.pcap

printf "Do you want to delete $INTERFACE.pcap? (y/N): "
read -r answer
case "$answer" in
    [Yy]|[Yy][Ee][Ss])
        echo "Deleting existing $INTERFACE.pcap..."
        sudo rm -f $INTERFACE.pcap
        ;;
    *)
        echo "Keeping existing file. Exiting..."
        exit 0
        ;;
esac
