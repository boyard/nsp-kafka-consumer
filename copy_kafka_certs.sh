#!/bin/bash
# Script to copy correct Kafka certificates from the pod

echo "🔐 Copying Kafka certificates from pod..."

# Configuration
DEPLOYER_HOST="172.18.116.65"
CLUSTER_HOST="10.215.1.21"
KAFKA_NAMESPACE="nsp-psa-restricted"
KAFKA_POD="nspos-kafka-0"
SSH_USER="root"

# Create certs directory if it doesn't exist
mkdir -p ./certs

# Function to copy certificate from pod to local via two-hop SSH
copy_cert() {
    local pod_file=$1
    local local_file=$2
    local temp_file="/tmp/$(basename $local_file).$$"
    
    echo "📋 Copying $pod_file to $local_file..."
    
    # Step 1: Copy from pod to cluster host
    ssh -o StrictHostKeyChecking=no ${SSH_USER}@${DEPLOYER_HOST} \
        "ssh -o StrictHostKeyChecking=no ${CLUSTER_HOST} \
        'kubectl cp ${KAFKA_NAMESPACE}/${KAFKA_POD}:${pod_file} ${temp_file}'"
    
    # Step 2: Copy from cluster host to deployer host
    ssh -o StrictHostKeyChecking=no ${SSH_USER}@${DEPLOYER_HOST} \
        "scp -o StrictHostKeyChecking=no ${CLUSTER_HOST}:${temp_file} ${temp_file}"
    
    # Step 3: Copy from deployer host to local
    scp -o StrictHostKeyChecking=no ${SSH_USER}@${DEPLOYER_HOST}:${temp_file} ${local_file}
    
    # Clean up temp files
    ssh -o StrictHostKeyChecking=no ${SSH_USER}@${DEPLOYER_HOST} \
        "rm -f ${temp_file} && ssh -o StrictHostKeyChecking=no ${CLUSTER_HOST} 'rm -f ${temp_file}'"
    
    if [ -f "$local_file" ] && [ -s "$local_file" ]; then
        echo "✅ Successfully copied $local_file"
    else
        echo "❌ Failed to copy $local_file"
    fi
}

# Copy CA certificate
copy_cert "/opt/nsp/os/ssl/ca_cert.pem" "./certs/ca_cert.pem"

# Copy client certificate from combined PEM (includes both cert and key)
copy_cert "/opt/nsp/os/ssl/nsp_external_combined.pem" "./certs/nsp_external_combined.pem"

# Extract client cert and key from combined PEM
if [ -f "./certs/nsp_external_combined.pem" ]; then
    echo "🔧 Extracting client certificate and key from combined PEM..."
    
    # Extract certificate
    awk '/-----BEGIN CERTIFICATE-----/,/-----END CERTIFICATE-----/' ./certs/nsp_external_combined.pem > ./certs/client_cert.pem
    
    # Extract private key
    awk '/-----BEGIN.*PRIVATE KEY-----/,/-----END.*PRIVATE KEY-----/' ./certs/nsp_external_combined.pem > ./certs/client_key.pem
    
    echo "✅ Extracted client certificate and key"
fi

# Also copy the internal CA for completeness
copy_cert "/opt/nsp/os/ssl/internal_ca_cert.pem" "./certs/internal_ca_cert.pem"

# Verify certificates
echo ""
echo "🔍 Verifying certificates..."
echo "CA Certificate:"
openssl x509 -in ./certs/ca_cert.pem -subject -issuer -noout 2>/dev/null || echo "❌ Invalid CA cert"

echo ""
echo "Client Certificate:"
openssl x509 -in ./certs/client_cert.pem -subject -issuer -noout 2>/dev/null || echo "❌ Invalid client cert"

echo ""
echo "✅ Certificate copy complete!"
