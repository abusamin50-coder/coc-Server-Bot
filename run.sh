#!/bin/bash
# Local development server runner

# Activate venv
source venv/bin/activate

# Set environment
export FLASK_ENV=development
export FLASK_DEBUG=1

# Run server
cd server
python -c "
from app import create_app

app = create_app()

print('🚀 Server running at http://localhost:5000')
print('📝 Login: admin / admin123')
print('⚠️  Press Ctrl+C to stop\n')

app.run(host='0.0.0.0', port=5000, debug=True)
"
