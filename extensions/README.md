# E-NOR Extensions

This folder contains custom extensions created for your robot! Extensions add new features, games, emotions, and more without modifying the core robot code.

## How Extensions Work

When you ask E-NOR to create a new feature (like "create a times tables quiz"), it creates a new folder here with the code for that feature.

## Extension Structure

Each extension is a folder containing:

```
my_extension/
├── manifest.json      # Required: extension metadata
├── handler.py         # Optional: Python logic
├── emotion.json       # Optional: custom emotion
├── jokes.json         # Optional: custom jokes
├── overlay.svg        # Optional: face overlay graphics
├── sounds/            # Optional: sound effects
├── ui.html            # Optional: custom UI panel
├── data/              # Optional: saved data
└── requirements.txt   # Optional: Python dependencies
```

## manifest.json Example

```json
{
  "id": "times_tables_quiz",
  "name": "Times Tables Quiz",
  "description": "A fun game to practice multiplication",
  "version": "1.0.0",
  "author": "Created by voice request",
  "type": "game",
  "enabled": true,
  "voice_triggers": [
    {
      "phrases": ["times tables", "multiplication quiz", "quiz me on maths"],
      "action": "start_quiz"
    }
  ]
}
```

## Managing Extensions

- **Enable/Disable**: Use the parent dashboard at `/admin`
- **Delete**: Remove the folder or use the dashboard
- **Reload**: Extensions are loaded when the server starts

## Creating Extensions

Extensions are typically created automatically when you ask E-NOR for new features via voice. The robot creates a GitHub issue, and the automated pipeline builds the extension.

You can also create extensions manually by:
1. Creating a new folder in this directory
2. Adding a `manifest.json` file
3. Adding any additional files needed
4. Restarting the E-NOR server
