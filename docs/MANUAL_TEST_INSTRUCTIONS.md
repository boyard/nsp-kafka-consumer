# Manual Test Instructions for NSP Kafka Consumer Fixes

## Test 1: Shutdown Handling (CTRL+C)

1. Start the consumer:
   ```bash
   cd /Users/engels/NSPlayground/KTnV
   source .venv/bin/activate
   python3 nsp_kafka_consumer.py --topics nsp-yang-model.change-notif --no-discovery
   ```

2. Wait for messages to appear (you should see KAFKA MESSAGE output)

3. Press CTRL+C

4. **Expected Result**: 
   - Consumer should display "Shutdown signal received" message
   - Process should terminate cleanly within 3 seconds
   - You should see the session summary and return to terminal prompt

## Test 2: Dynamic Topic Management

1. Start the consumer:
   ```bash
   cd /Users/engels/NSPlayground/KTnV
   source .venv/bin/activate
   python3 nsp_kafka_consumer.py
   ```

2. Select a single topic from the menu (e.g., nsp-yang-model.change-notif)

3. Wait for messages to start flowing

4. While messages are being displayed, type `manage` and press Enter

5. In the management menu:
   - Type `add` and press Enter
   - Search for another topic (e.g., `search:health-alarms`)
   - Select the topic

6. Type `done` to exit management mode

7. **Expected Result**:
   - Messages should continue flowing after adding the new topic
   - You should see messages from both topics
   - No message flow interruption

## What We Fixed

### Issue 1: Shutdown Hanging
- Removed consumer close from signal handler (was causing deadlock)
- Added threaded consumer close with 3-second timeout
- Reduced poll timeout from 1000ms to 500ms for better shutdown response
- Added checks in main loop to exit quickly when shutdown signal received

### Issue 2: Dynamic Topic Management Breaking Message Flow
- Changed from consumer recreation to using `subscribe()` method directly
- Added longer timeout (5 seconds) for initial poll after subscription change
- Removed complex consumer recreation logic that was causing issues
- Kept subscription changes simple and atomic

## Key Changes Made

1. **Signal Handler** (`_signal_handler`):
   - No longer tries to close consumer (prevents hanging)
   - Just sets `running = False` flag

2. **Topic Updates** (`_update_topics`):
   - Uses `consumer.subscribe()` instead of recreating consumer
   - Forces a poll with 5-second timeout to ensure subscription takes effect
   - Simpler rollback mechanism if update fails

3. **Main Loop**:
   - Shorter poll timeout (500ms vs 1000ms)
   - Checks `running` flag more frequently
   - Ignores errors during shutdown

4. **Cleanup** (`_cleanup`):
   - Uses threaded close with 3-second timeout
   - Won't hang if consumer close fails

## Verification Steps

To verify the fixes are working:

1. **For Shutdown**: Time how long it takes from pressing CTRL+C to getting back to prompt. Should be < 3 seconds.

2. **For Dynamic Topics**: Count messages before and after adding topics. Message flow should not stop.

## If Issues Persist

If you still experience issues:

1. Check the log file:
   ```bash
   tail -f nsp_kafka_consumer.log
   ```

2. Try the test scripts:
   ```bash
   python3 test_consumer_fixes.py
   python3 test_dynamic_topics.py
   ```

3. Look for any error messages during topic updates or shutdown

The consumer should now handle both shutdown and dynamic topic management properly!
