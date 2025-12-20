# Dog Mode Extension

A fun extension that transforms E-NOR into a playful dog companion with floppy ears, a tongue sticking out, and various dog sounds!

## Features

- **Visual Transformation**: Adds floppy dog ears and a pink tongue overlay to E-NOR's face
- **Dog Sounds**: Multiple realistic dog barks, woofs, and yips
- **Interactive Behavior**: Responds with dog-like enthusiasm and actions
- **Voice Activation**: Multiple phrases to activate/deactivate dog mode

## Voice Commands

### Activation
- "dog mode" / "activate dog mode" / "turn on dog mode"
- "become a dog" / "puppy mode" / "woof mode"

### Deactivation  
- "deactivate dog mode" / "turn off dog mode" / "stop dog mode"
- "normal mode" / "exit dog mode"

### Dog Sounds
- "bark" / "woof" / "make dog sounds"

## Files

- `manifest.json` - Extension metadata and voice triggers
- `handler.py` - Python logic for dog behaviors
- `overlay.svg` - SVG graphics for dog ears and tongue
- `sounds/` - Dog sound effects (placeholders for actual audio files)
- `README.md` - This documentation

## Sound Files (Need Real Audio)

The extension includes placeholder files that should be replaced with actual audio:
- `woof_hello.wav` - Greeting bark
- `woof_goodbye.wav` - Goodbye bark  
- `woof1.wav`, `woof2.wav`, `woof3.wav` - Happy barks
- `bark1.wav`, `bark2.wav` - Various barks and yips

## How It Works

1. **Activation**: When dog mode is activated, E-NOR shows dog ears and tongue overlay, plays greeting sound, and enters an excited state
2. **Interactive Response**: While in dog mode, E-NOR responds with dog-like enthusiasm to interactions
3. **Sound Effects**: Random dog sounds and actions create engaging doggy behavior
4. **Deactivation**: Returns E-NOR to normal mode, hiding overlays and returning to regular personality

Created for Ronnie via voice request! 🐕