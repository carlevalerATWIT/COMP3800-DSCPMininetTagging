#!/bin/bash

# Reset QoS on all ports
for intf in s1-eth1 s1-eth2; do
  sudo ovs-vsctl -- clear Port $intf qos
done

# Create queues and apply to s1-eth1 and s1-eth2
for intf in s1-eth1 s1-eth2; do
  echo "[+] Attaching queues to $intf..."
  sudo ovs-vsctl -- set Port $intf qos=@newqos \
    -- --id=@newqos create QoS type=linux-htb other-config:max-rate=100000000 \
       queues:0=@q0 queues:1=@q1 \
    -- --id=@q0 create Queue other-config:min-rate=20000000 other-config:max-rate=50000000 \
    -- --id=@q1 create Queue other-config:min-rate=80000000 other-config:max-rate=100000000
done

echo "[-] Queue setup complete."
