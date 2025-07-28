#!/bin/bash

set -e

echo "🚀 Building Persona-Driven Document Intelligence System..."

# Build Docker image
docker build --platform linux/amd64 -t persona-document-analyst:latest . || {
    echo "❌ Docker build failed!"
    exit 1
}

echo "✅ Docker image built successfully!"

# Test with sample collections
for collection in test_collections/*/; do
    if [ -f "$collection/challenge1b_input.json" ]; then
        echo "🧪 Testing collection: $(basename "$collection")"
        
        # Create test output directory
        mkdir -p "$collection/output"
        
        # Run analysis
        docker run --rm \
            -v "$(pwd)/$collection:/app/input" \
            -v "$(pwd)/$collection/output:/app/output" \
            --network none \
            persona-document-analyst:latest || {
            echo "❌ Test failed for $(basename "$collection")"
            continue
        }
        
        echo "✅ Test completed for $(basename "$collection")"
        
        # Show sample output
        if [ -f "$collection/output/challenge1b_output.json" ]; then
            echo "📄 Sample output:"
            head -30 "$collection/output/challenge1b_output.json"
            echo ""
        fi
    fi
done

echo ""
echo "🎉 Setup complete! Your persona-driven document analyst is ready."
echo ""
echo "To use with your own document collections:"
echo "1. Create input/challenge1b_input.json with your configuration"
echo "2. Copy PDF files to input/ directory"  
echo "3. Run: docker run --rm -v \$(pwd)/input:/app/input -v \$(pwd)/output:/app/output --network none persona-document-analyst:latest"
echo "4. Check output/challenge1b_output.json for results"
