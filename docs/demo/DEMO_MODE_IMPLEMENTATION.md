# 🎬 Demo Mode Implementation

This document describes the Demo Mode feature that allows toggling demo-specific enhancements on/off.

---

## 📋 Overview

Demo Mode is a toggle feature that shows/hides advanced visualization features designed for presentations:
- Response Time Display
- Technology Flow Visualization (Tech Badges)
- Confidence Score Display
- Real-time Processing Indicators
- Quick Action Buttons

**Default State**: Demo Mode is **OFF** by default, so all demo features are hidden in normal usage.

---

## 🎯 Features Enabled in Demo Mode

### 1. ⚡ Response Time Display
- Shows response time in milliseconds/seconds below bot messages
- Color-coded: Green (<2s), Yellow (2-5s), Red (>5s)

### 2. 🏷️ Technology Flow Visualization
- Displays tech badges: NLP, RAG, LLM
- Shows which technologies are used for each response

### 3. 📊 Confidence Score Display
- Shows intent classification confidence percentage
- Color-coded based on confidence level

### 4. 🔄 Real-time Processing Indicators
- Shows processing steps during response generation:
  - 🔍 Analyzing query...
  - 🧠 Detecting intent: [intent] ([confidence]%)
  - 📚 Retrieving context from knowledge base...
  - 🤖 Generating response with LLM...
  - ✅ Response ready!

### 5. 🚀 Quick Action Buttons
- Shows quick action buttons below welcome message
- One-click access to common questions

---

## 🔧 How to Use

### Enable Demo Mode

**Method 1: Toggle Button**
- Click the "🎬 Demo Mode: OFF" button in the chatbot header
- Button will change to "🎬 Demo Mode: ON" when active

**Method 2: URL Parameter**
- Add `?demo=true` to the URL: `http://yoursite.com/?demo=true`

**Method 3: localStorage**
- Demo mode state is saved in localStorage
- If enabled, it persists across page reloads

### Disable Demo Mode
- Click the "🎬 Demo Mode: ON" button again
- Or remove the URL parameter and clear localStorage

---

## 📁 Files Modified

### Frontend Files

1. **`frontend/templates/main.html`**
   - Added demo mode toggle button in header
   - Added quick action buttons (hidden by default)
   - Added processing steps container

2. **`frontend/static/js/chat.js`**
   - Added `demoMode` property (default: `false`)
   - Added `initDemoMode()` - Initialize from URL/localStorage
   - Added `toggleDemoMode()` - Toggle demo mode on/off
   - Added `updateDemoModeUI()` - Update UI based on mode
   - Added `showProcessingSteps()` - Display processing indicators
   - Added `updateProcessingSteps()` - Update with real data
   - Added `hideProcessingSteps()` - Hide processing indicators
   - Modified `addMessage()` - Only show metrics in demo mode
   - Modified `sendMessage()` - Show processing steps in demo mode

3. **`frontend/static/css/faix-style.css`**
   - Added `.demo-mode-toggle` styling
   - Added `.chatbot-header-actions` container styling
   - Added `.processing-steps` and `.processing-step` styling
   - All existing demo feature styles remain (now controlled by demo mode)

---

## 🎨 Visual Changes

### Header (Demo Mode OFF)
```
┌─────────────────────────────────────┐
│ FAIX Assistant    [🎬 Demo Mode: OFF] [-]
└─────────────────────────────────────┘
```

### Header (Demo Mode ON)
```
┌─────────────────────────────────────┐
│ FAIX Assistant    [🎬 Demo Mode: ON] [-]
└─────────────────────────────────────┘
```

### Processing Steps (Demo Mode Only)
```
┌─────────────────────────────────────┐
│ 🔍 Analyzing query...               │
│ 🧠 Detecting intent: course_info (95%)│
│ 📚 Retrieving context...            │
│ 🤖 Generating response with LLM...  │
│ ✅ Response ready!                  │
└─────────────────────────────────────┘
```

---

## 🔄 Behavior

### When Demo Mode is OFF (Default)
- ❌ Response time not displayed
- ❌ Tech badges not displayed
- ❌ Confidence score not displayed
- ❌ Processing steps not shown
- ❌ Quick action buttons hidden
- ✅ Normal typing indicator shown

### When Demo Mode is ON
- ✅ Response time displayed
- ✅ Tech badges displayed
- ✅ Confidence score displayed
- ✅ Processing steps shown during request
- ✅ Quick action buttons visible
- ✅ Normal typing indicator + processing steps

---

## 💾 State Persistence

- Demo mode state is saved in `localStorage` as `chatbot_demo_mode`
- Persists across page reloads
- Can be enabled via URL parameter for one-time demos
- URL parameter takes precedence over localStorage

---

## 🧪 Testing

### Test Demo Mode Toggle
1. Open chatbot
2. Click demo mode toggle button
3. Verify quick actions appear/disappear
4. Send a message
5. Verify metrics appear/disappear

### Test Processing Steps
1. Enable demo mode
2. Send a message
3. Verify processing steps appear sequentially
4. Verify steps update with real intent/confidence data

### Test URL Parameter
1. Add `?demo=true` to URL
2. Reload page
3. Verify demo mode is enabled
4. Remove parameter
5. Reload page
6. Verify demo mode state from localStorage

---

## 📝 Code Examples

### Check Demo Mode State
```javascript
if (chatbot.demoMode) {
    // Demo mode is enabled
}
```

### Programmatically Toggle Demo Mode
```javascript
chatbot.toggleDemoMode();
```

### Enable Demo Mode Programmatically
```javascript
chatbot.demoMode = true;
chatbot.updateDemoModeUI();
localStorage.setItem('chatbot_demo_mode', 'true');
```

---

## 🎯 Use Cases

1. **Presentations**: Enable demo mode to show technical capabilities
2. **Development**: Test visualization features
3. **Training**: Show internal workings of the system
4. **Production**: Keep demo mode OFF for clean user interface

---

## ⚠️ Notes

- Demo mode does not affect chatbot functionality, only visualization
- All demo features are client-side only
- Processing steps timing is simulated (not real-time backend events)
- Quick action buttons are always rendered but hidden when demo mode is OFF

---

**Last Updated**: January 2025
**Status**: ✅ Implemented
