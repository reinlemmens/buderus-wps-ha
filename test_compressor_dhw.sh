#!/bin/bash
# Monitor compressor and DHW temperature during extra DHW heating
# Run on homeassistant.local

echo "==================================================================="
echo "Compressor & DHW Temperature Monitor"
echo "==================================================================="
echo "Extra DHW heating requested (1 hour)"
echo ""

cd ~/buderus-testing

for i in {1..20}; do
    echo "--- Check $i/20 ($(date +%H:%M:%S)) ---"

    # Check compressor frequency
    FREQ=$(sudo venv/bin/wps-cli read COMPRESSOR_REAL_FREQUENCY 2>&1 | grep "=" | awk '{print $3}')
    echo "Compressor: $FREQ Hz"

    # Check DHW temperature via broadcast
    TEMP=$(sudo venv/bin/python3 -c "
import sys
sys.path.insert(0, '.')
from buderus_wps import USBtinAdapter, BroadcastMonitor
adapter = USBtinAdapter('/dev/ttyACM0', timeout=5.0)
adapter.connect()
monitor = BroadcastMonitor(adapter)
cache = monitor.collect(duration=3.0)
reading = cache.get_by_idx_and_base(78, 0x0402)
if reading:
    print(f'{reading.temperature:.1f}')
else:
    print('N/A')
adapter.disconnect()
" 2>&1 | tail -1)

    echo "DHW Temp: ${TEMP}°C"

    # Check if compressor is running
    if [[ "$FREQ" != "0" ]]; then
        echo "✓ COMPRESSOR RUNNING!"
    fi

    echo ""
    sleep 15
done

echo "==================================================================="
echo "Monitoring complete"
