# Speech-to-Text Feature - Manual Testing Guide


To manually test the Speech-to-Text feature:

1. BROWSER COMPATIBILITY TEST:
   - Open the chatbot in Chrome or Edge (Web Speech API support)
   - Verify microphone button is visible
   - Open in Firefox/Safari and verify button is hidden (if not supported)

2. MICROPHONE PERMISSION TEST:
   - Click the microphone button
   - Grant microphone permission when prompted
   - Verify button turns red and shows "Listening..." status

3. RECORDING TEST:
   - Click microphone button to start recording
   - Speak clearly: "What courses are available?"
   - Watch the input field update with transcribed text
   - Verify message is automatically sent when you stop speaking

4. BUTTON STATES TEST:
   - Inactive: Gray button (default)
   - Recording: Red button with pulsing animation
   - Error: Red border (if error occurs)

5. ERROR HANDLING TEST:
   - Deny microphone permission - verify error message
   - Speak nothing for 5+ seconds - verify timeout handling
   - Test with poor audio quality - verify graceful degradation

6. INTEGRATION TEST:
   - Use voice input to ask: "How do I register?"
   - Verify transcribed text appears in chat
   - Verify bot responds appropriately
   - Check conversation history includes voice-transcribed message

7. EDGE CASES:
   - Click microphone while already recording (should stop)
   - Click microphone while loading (should be disabled)
   - Speak very long sentences (verify text handling)
   - Speak with background noise (verify accuracy)

EXPECTED BEHAVIOR:
[OK] Microphone button visible in supported browsers
[OK] Button changes color when recording
[OK] Transcribed text appears in input field
[OK] Message auto-sends after speech ends
[OK] Error messages shown for permission/network issues
[OK] Status indicator updates ("Listening..." -> "Online")
