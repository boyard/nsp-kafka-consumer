#!/usr/bin/env python3
"""
NSP Intelligent Discovery Script v3.0

Proper workflow:
1. Connect to NSP Deployer Host via SSH
2. Parse k8s-deployer.yml to find NSP Cluster Host IPs
3. Connect to first NSP Cluster Host 
4. Discover NSP services, Kafka brokers, and UI endpoints
5. Download/configure SSL certificates
6. Generate working configuration files

This approach correctly separates deployer functions from cluster functions.

Author: Agent Mode
"""

import os
import sys
import json
import yaml
import requests
import configparser
import subprocess
import time
import getpass
import base64
import argparse
from datetime import datetime
from urllib3.exceptions import InsecureRequestWarning

# Suppress SSL warnings
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

VERBOSE = True
DEBUG = False  # Set to True for detailed output like listing secrets
SETUP_CACHE_FILE = '.nsp_setup_cache.json'
CONFIG_FILE = 'nsp_config.ini'

def log(message):
    """Enhanced logging with timestamps"""
    if VERBOSE:
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")

def test_ssh_connection(host, username, password=None):
    """Test SSH connection with key or password"""
    try:
        if password:
            # Test with password using sshpass
            test_cmd = f'sshpass -p "{password}" ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no {username}@{host} "echo SSH_OK"'
        else:
            # Test with SSH key
            test_cmd = f'ssh -o ConnectTimeout=10 -o BatchMode=yes -o StrictHostKeyChecking=no {username}@{host} "echo SSH_OK"'
        
        result = subprocess.getoutput(test_cmd)
        return "SSH_OK" in result
    except Exception as e:
        log(f"SSH test error: {e}")
        return False

def execute_ssh_command(host, username, command, password=None):
    """Execute command on remote host via SSH"""
    try:
        if password:
            cmd = f'sshpass -p "{password}" ssh -o StrictHostKeyChecking=no {username}@{host} "{command}"'
        else:
            cmd = f'ssh -o BatchMode=yes -o StrictHostKeyChecking=no {username}@{host} "{command}"'
        
        log(f"💻 Executing on {host}: {command}")
        result = subprocess.getoutput(cmd)
        
        # Filter out SSH banners
        return filter_ssh_output(result)
    except Exception as e:
        log(f"SSH command error: {e}")
        return None

def filter_ssh_output(raw_output):
    """Filter out SSH login banners and system messages"""
    if not raw_output:
        return ""
    
    lines = raw_output.split('\n')
    filtered_lines = []
    
    ignore_patterns = [
        "authorized uses only",
        "all activity may be monitored", 
        "warning:",
        "last login:",
        "welcome to"
    ]
    
    for line in lines:
        line_lower = line.lower().strip()
        
        if not line_lower:
            continue
            
        is_banner = any(pattern in line_lower for pattern in ignore_patterns)
        if is_banner:
            # Silently filter out banners without logging
            continue
            
        filtered_lines.append(line)
    
    return '\n'.join(filtered_lines)

def get_deployer_connection():
    """Get NSP Deployer Host connection details"""
    log("🔍 Getting NSP Deployer Host connection details...")
    
    # Check cache
    if os.path.exists(SETUP_CACHE_FILE):
        try:
            with open(SETUP_CACHE_FILE, 'r') as f:
                cache = json.load(f)
            
            if cache.get('deployer_host') and cache.get('username'):
                cached_conn = f"{cache['username']}@{cache['deployer_host']}"
                log(f"📋 Found cached connection: {cached_conn}")
                
                if input(f"Use cached connection ({cached_conn})? [Y/n]: ").lower() != 'n':
                    # Test cached connection
                    if test_ssh_connection(cache['deployer_host'], cache['username'], cache.get('password')):
                        log("✅ Cached connection still works!")
                        return cache['deployer_host'], cache['username'], cache.get('password')
                    else:
                        log("⚠️  Cached connection failed")
        except Exception as e:
            log(f"Cache error: {e}")
    
    # Get new connection details
    log("📝 Enter NSP Deployer Host details:")
    deployer_host = input("NSP Deployer Host IP: ").strip()
    username = input("SSH Username [root]: ").strip() or "root"
    
    # Try SSH key first
    log(f"🔌 Testing SSH connection to {username}@{deployer_host}...")
    password = None
    
    if not test_ssh_connection(deployer_host, username):
        log("🔐 SSH key failed, need password")
        password = getpass.getpass(f"SSH Password for {username}@{deployer_host}: ")
        
        if not test_ssh_connection(deployer_host, username, password):
            log("❌ SSH connection failed with password")
            return None, None, None
    else:
        log("✅ SSH key authentication successful")
    
    # Cache working connection
    cache_data = {
        'deployer_host': deployer_host,
        'username': username,
        'password': password,
        'timestamp': time.time()
    }
    
    with open(SETUP_CACHE_FILE, 'w') as f:
        json.dump(cache_data, f)
    log(f"✅ Cached connection to {SETUP_CACHE_FILE}")
    
    return deployer_host, username, password

def find_cluster_hosts_from_deployer(deployer_host, username, password):
    """Parse k8s-deployer.yml to find NSP cluster host IPs"""
    log("🔍 Finding NSP cluster hosts from k8s-deployer.yml...")
    
    # Find k8s-deployer.yml file
    find_commands = [
        "find /opt/nsp -name 'k8s-deployer.yml' 2>/dev/null | head -1",
        "find /root -name 'k8s-deployer.yml' 2>/dev/null | head -1", 
        "find /home -name 'k8s-deployer.yml' 2>/dev/null | head -1",
        "ls k8s-deployer.yml 2>/dev/null"
    ]
    
    deployer_yml_path = None
    for cmd in find_commands:
        result = execute_ssh_command(deployer_host, username, cmd, password)
        if result and result.strip() and not result.startswith("find:"):
            deployer_yml_path = result.strip()
            log(f"📄 Found k8s-deployer.yml at: {deployer_yml_path}")
            break
    
    if not deployer_yml_path:
        log("⚠️  k8s-deployer.yml not found, trying kubectl fallback")
        return find_cluster_hosts_kubectl_fallback(deployer_host, username, password)
    
    # Read the YAML file
    cat_cmd = f"cat '{deployer_yml_path}'"
    yml_content = execute_ssh_command(deployer_host, username, cat_cmd, password)
    
    if not yml_content:
        log("⚠️  Could not read k8s-deployer.yml")
        return find_cluster_hosts_kubectl_fallback(deployer_host, username, password)
    
    # Parse YAML to extract cluster IPs
    cluster_hosts = []
    try:
        # Parse YAML content
        yaml_data = yaml.safe_load(yml_content)
        log("✅ Successfully parsed k8s-deployer.yml")
        
        # Look for cluster configuration sections
        def extract_ips_from_dict(data, path=""):
            """Recursively extract IP addresses from YAML structure"""
            ips = []
            if isinstance(data, dict):
                for key, value in data.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    # Look for common cluster-related keys
                    if any(keyword in key.lower() for keyword in ['cluster', 'node', 'worker', 'master', 'host', 'ip']):
                        log(f"🔍 Checking section: {current_path}")
                    
                    if isinstance(value, str):
                        # Check if value looks like an IP address
                        import re
                        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
                        found_ips = re.findall(ip_pattern, value)
                        for ip in found_ips:
                            if ip != deployer_host:  # Don't include deployer host
                                ips.append(ip)
                                log(f"  🎯 Found IP in {current_path}: {ip}")
                    
                    elif isinstance(value, (dict, list)):
                        ips.extend(extract_ips_from_dict(value, current_path))
            
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    ips.extend(extract_ips_from_dict(item, f"{path}[{i}]"))
            
            return ips
        
        # Extract IPs preserving order (first found first)
        all_ips = extract_ips_from_dict(yaml_data)
        cluster_hosts = []
        for ip in all_ips:
            if ip not in cluster_hosts:  # Remove duplicates but preserve order
                cluster_hosts.append(ip)
        
    except Exception as e:
        log(f"⚠️  Error parsing YAML: {e}")
        # Try simple regex fallback on raw content
        import re
        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        all_ips = re.findall(ip_pattern, yml_content)
        cluster_hosts = [ip for ip in set(all_ips) if ip != deployer_host]
    
    if cluster_hosts:
        log(f"✅ Found {len(cluster_hosts)} potential cluster hosts: {cluster_hosts}")
        return cluster_hosts
    else:
        log("⚠️  No cluster hosts found in k8s-deployer.yml, using kubectl fallback")
        return find_cluster_hosts_kubectl_fallback(deployer_host, username, password)

def find_cluster_hosts_kubectl_fallback(deployer_host, username, password):
    """Fallback method to find cluster hosts using kubectl"""
    log("🔄 Using kubectl to find cluster hosts...")
    
    kubectl_cmd = "kubectl get nodes -o wide --no-headers | awk '{print $6}' | grep -v '<none>' | sort -u"
    result = execute_ssh_command(deployer_host, username, kubectl_cmd, password)
    
    if result:
        import re
        ip_pattern = r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$'
        potential_ips = [ip.strip() for ip in result.split('\n') if ip.strip()]
        cluster_hosts = [ip for ip in potential_ips if re.match(ip_pattern, ip) and ip != deployer_host]
        
        if cluster_hosts:
            log(f"✅ Found cluster hosts via kubectl: {cluster_hosts}")
            return cluster_hosts
    
    log("⚠️  No cluster hosts found via kubectl")
    return []

def find_working_cluster_host(cluster_hosts, deployer_host, username, password):
    """Find the first working NSP cluster host via deployer host"""
    log("🔍 Finding working NSP cluster host...")
    
    expected_nsp_namespaces = ['nsp-psa-restricted', 'nsp-psa-baseline', 'nsp-psa-privileged']
    
    for cluster_host in cluster_hosts:
        log(f"🔍 Testing cluster host: {cluster_host}")
        
        # Test SSH connection through deployer host (two-hop SSH)
        test_cmd = f"ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=10 {cluster_host} 'echo test'"
        ssh_test = execute_ssh_command(deployer_host, username, test_cmd, password)
        
        if not ssh_test or 'test' not in ssh_test:
            log(f"❌ Cannot SSH to {cluster_host} via deployer")
            continue
        
        log(f"✅ SSH connection to {cluster_host} works via deployer")
        
        # Check for NSP namespaces via deployer host
        ns_cmd = f"ssh -o BatchMode=yes -o StrictHostKeyChecking=no {cluster_host} 'kubectl get namespaces -o name'"
        ns_result = execute_ssh_command(deployer_host, username, ns_cmd, password)
        
        if ns_result:
            namespaces = [line.replace('namespace/', '') for line in ns_result.split('\n') if line.strip()]
            found_nsp_ns = [ns for ns in namespaces if ns in expected_nsp_namespaces]
            
            if found_nsp_ns:
                log(f"✅ Found working NSP cluster host: {cluster_host}")
                log(f"   NSP namespaces: {found_nsp_ns}")
                return cluster_host
            else:
                log(f"⚠️  {cluster_host} has no NSP namespaces")
        else:
            log(f"⚠️  Could not get namespaces from {cluster_host}")
    
    log("❌ No working NSP cluster host found")
    return None

def discover_kafka_pods(cluster_host, deployer_host, username, password):
    """Direct Kafka pod discovery - streamlined approach"""
    log(f"🔍 Discovering Kafka pods on {cluster_host}...")
    
    # Determine if we need to SSH through deployer or directly to cluster
    if cluster_host == deployer_host:
        # Direct connection to deployer (which is also cluster host)
        def run_kubectl(cmd):
            return execute_ssh_command(cluster_host, username, cmd, password)
    else:
        # Two-hop SSH through deployer to cluster host
        def run_kubectl(cmd):
            ssh_cmd = f"ssh -o BatchMode=yes -o StrictHostKeyChecking=no {cluster_host} '{cmd}'"
            return execute_ssh_command(deployer_host, username, ssh_cmd, password)
    
    # Find Kafka pods directly
    kafka_cmd = "kubectl get pods -A | grep kafka"
    kafka_result = run_kubectl(kafka_cmd)
    
    if not kafka_result:
        log("❌ No Kafka pods found")
        return {}
    
    kafka_pods = []
    log(f"🎯 Found Kafka pods:")
    
    for line in kafka_result.split('\n'):
        if line.strip() and 'kafka' in line.lower():
            parts = line.split()
            if len(parts) >= 2:
                namespace = parts[0]
                pod_name = parts[1]
                status = parts[2] if len(parts) > 2 else 'Unknown'
                
                kafka_pods.append({
                    'namespace': namespace,
                    'pod_name': pod_name,
                    'status': status,
                    'full_line': line.strip()
                })
                log(f"  📦 {namespace}/{pod_name} ({status})")
    
    if not kafka_pods:
        log("❌ No valid Kafka pods found")
        return {}
    
    # Pick the main Kafka broker (usually the one ending with -0 or containing 'nspos')
    main_kafka = None
    for pod in kafka_pods:
        if 'nspos-kafka' in pod['pod_name'] or pod['pod_name'].endswith('-0'):
            main_kafka = pod
            break
    
    if not main_kafka:
        main_kafka = kafka_pods[0]  # Fallback to first pod
    
    log(f"🎯 Selected main Kafka pod: {main_kafka['namespace']}/{main_kafka['pod_name']}")
    
    # Also discover ingress IP for NSP UI
    log("🔍 Looking for NSP UI ingress IP...")
    ingress_cmd = "kubectl get svc --all-namespaces | grep -i ingress"
    ingress_result = run_kubectl(ingress_cmd)
    
    ingress_ip = None
    if ingress_result:
        for line in ingress_result.split('\n'):
            if 'LoadBalancer' in line:
                parts = line.split()
                if len(parts) >= 5:
                    external_ip = parts[4]  # Usually column 5 has EXTERNAL-IP
                    if external_ip and external_ip != '<pending>' and not external_ip.startswith('<'):
                        ingress_ip = external_ip
                        log(f"🌐 Found NSP UI ingress IP: {ingress_ip}")
                        break
    
    if not ingress_ip:
        log("⚠️  No ingress IP found for NSP UI")
    
    return {
        'kafka_pods': kafka_pods,
        'main_kafka': main_kafka,
        'ingress_ip': ingress_ip
    }

def extract_kafka_bootstrap_servers(cluster_host, deployer_host, username, password, kafka_namespace):
    """Extract Kafka bootstrap servers from Kubernetes services"""
    log(f"🔍 Extracting Kafka services from namespace: {kafka_namespace}")
    
    # Determine SSH method
    if cluster_host == deployer_host:
        def run_kubectl(cmd):
            return execute_ssh_command(cluster_host, username, cmd, password)
    else:
        def run_kubectl(cmd):
            ssh_cmd = f"ssh -o BatchMode=yes -o StrictHostKeyChecking=no {cluster_host} '{cmd}'"
            return execute_ssh_command(deployer_host, username, ssh_cmd, password)
    
    # Get Kafka services
    svc_cmd = f"kubectl get svc -n {kafka_namespace} | grep kafka"
    svc_result = run_kubectl(svc_cmd)
    
    if not svc_result:
        log("⚠️  No Kafka services found in namespace")
        return None
    
    # Parse service information
    for line in svc_result.split('\n'):
        if 'kafka' in line.lower() and 'ClusterIP' in line:
            parts = line.split()
            if len(parts) >= 3:
                svc_name = parts[0]
                cluster_ip = parts[2]
                ports = parts[4] if len(parts) > 4 else '9092'
                
                # Extract port number from format like "9092/TCP"
                port = ports.split('/')[0] if '/' in ports else ports
                if ',' in port:
                    port = port.split(',')[0]  # Take first port if multiple
                
                bootstrap_server = f"{cluster_ip}:{port}"
                log(f"✅ Found Kafka service: {svc_name} -> {bootstrap_server}")
                return bootstrap_server
    
    return None

def extract_kafka_config_from_pod(cluster_host, deployer_host, username, password, kafka_namespace, kafka_pod_name):
    """Extract Kafka configuration directly from the pod"""
    log(f"🔍 Extracting config from pod: {kafka_namespace}/{kafka_pod_name}")
    
    # Determine SSH method
    if cluster_host == deployer_host:
        def run_kubectl(cmd):
            return execute_ssh_command(cluster_host, username, cmd, password)
    else:
        def run_kubectl(cmd):
            ssh_cmd = f"ssh -o BatchMode=yes -o StrictHostKeyChecking=no {cluster_host} '{cmd}'"
            return execute_ssh_command(deployer_host, username, ssh_cmd, password)
    
    # Try to get pod environment variables or config
    env_cmd = f"kubectl exec -n {kafka_namespace} {kafka_pod_name} -- env | grep -i kafka"
    env_result = run_kubectl(env_cmd)
    
    if env_result:
        log(f"🔍 Found Kafka environment variables:")
        for line in env_result.split('\n'):
            if 'BOOTSTRAP' in line.upper() or 'BROKER' in line.upper():
                log(f"  {line}")
                # Parse bootstrap servers if found
                if '=' in line:
                    value = line.split('=', 1)[1]
                    if ':' in value and not value.startswith('/'):
                        return value
    
    # Fallback: try to get service IP for this pod's service
    return None

def discover_kafka_config(cluster_host, deployer_host, username, password, discovery_results):
    """Discover Kafka configuration from the cluster"""
    log("🔍 Discovering Kafka configuration from cluster...")
    
    kafka_pods = discovery_results.get('kafka_pods', [])
    main_kafka = discovery_results.get('main_kafka')
    
    if not main_kafka:
        log("❌ No main Kafka pod found for configuration extraction")
        return {'bootstrap_servers': 'localhost:9092'}  # Default fallback
    
    kafka_namespace = main_kafka['namespace']
    kafka_pod_name = main_kafka['pod_name']
    
    log(f"🎯 Extracting Kafka config from {kafka_namespace}/{kafka_pod_name}")
    
    # Method 1: Try to get Kafka service information
    bootstrap_servers = extract_kafka_bootstrap_servers(cluster_host, deployer_host, username, password, kafka_namespace)
    
    # Method 2: If that fails, try to read config from the Kafka pod itself
    if not bootstrap_servers or bootstrap_servers == 'TBD':
        bootstrap_servers = extract_kafka_config_from_pod(cluster_host, deployer_host, username, password, kafka_namespace, kafka_pod_name)
    
    # Method 3: Fallback to service discovery pattern
    if not bootstrap_servers or bootstrap_servers == 'TBD':
        bootstrap_servers = f"{cluster_host}:9092"  # Common default
        log(f"⚠️  Using fallback bootstrap servers: {bootstrap_servers}")
    
    return {'bootstrap_servers': bootstrap_servers}

def get_nsp_ui_credentials(suggested_ip=None):
    """Get NSP UI credentials and test authentication"""
    log("🔍 Getting NSP UI credentials...")
    
    # Suggest discovered ingress IP if available
    if suggested_ip:
        nsp_ui_ip = input(f"Enter NSP UI IP address [{suggested_ip}]: ").strip()
        if not nsp_ui_ip:
            nsp_ui_ip = suggested_ip
            log(f"✅ Using discovered ingress IP: {nsp_ui_ip}")
    else:
        nsp_ui_ip = input("Enter NSP UI IP address: ").strip()
    
    nsp_username = input("Enter NSP Username: ").strip()
    nsp_password = getpass.getpass("Enter NSP Password: ")
    
    # Test authentication
    try:
        url = f"https://{nsp_ui_ip}/rest-gateway/rest/api/v1/auth/token"
        payload = {"grant_type": "client_credentials"}
        
        response = requests.post(
            url, 
            auth=(nsp_username, nsp_password), 
            json=payload, 
            verify=False,
            timeout=30
        )
        response.raise_for_status()
        
        token_data = response.json()
        access_token = token_data['access_token']
        
        log(f"✅ NSP Authentication successful! Token: {access_token[:10]}...")
        return nsp_ui_ip, nsp_username, nsp_password, access_token
        
    except Exception as e:
        log(f"❌ NSP Authentication failed: {e}")
        return nsp_ui_ip, nsp_username, nsp_password, None

def handle_ssl_certificates(cluster_host, deployer_host, username, password, kafka_namespace, kafka_pod_name):
    """Handle SSL certificate management"""
    log("🔍 Managing SSL certificates...")
    
    certs_dir = './certs'
    if not os.path.exists(certs_dir):
        log("Creating certs directory...")
        os.makedirs(certs_dir, exist_ok=True)
    
    # Determine SSH method
    if cluster_host == deployer_host:
        def run_kubectl(cmd):
            return execute_ssh_command(cluster_host, username, cmd, password)
    else:
        def run_kubectl(cmd):
            ssh_cmd = f"ssh -o BatchMode=yes -o StrictHostKeyChecking=no {cluster_host} '{cmd}'"
            return execute_ssh_command(deployer_host, username, ssh_cmd, password)
    
    # First, try to copy certificates directly from the Kafka pod
    log("🌐 Copying SSL certificates from Kafka pod...")
    ssl_path = "/opt/nsp/os/ssl"
    
    # List available certificates in the pod
    list_cmd = f"kubectl exec -n {kafka_namespace} {kafka_pod_name} -- ls -la {ssl_path}/"
    list_result = run_kubectl(list_cmd)
    
    if list_result:
        log(f"📋 Available certificates in {kafka_pod_name}:{ssl_path}:")
        log(list_result)
    
    # Define external certificate files to copy (excluding internal ones)
    cert_files_to_copy = [
        'ca_cert.pem',
        'ca_cert.pem.exportcert',
        'nsp.key',
        'nsp.keystore',
        'nsp.truststore',
        'nsp_external_combined.pem',
        'nsp_keystore.p12',
        'nsp_truststore.p12'
    ]
    
    copied_files = []
    # Copy each certificate file with its original name using two-hop method
    for cert_filename in cert_files_to_copy:
        # Generate unique tmp filename to avoid conflicts
        remote_tmp = f"/tmp/{cert_filename.replace('.', '_')}-{int(time.time())}"
        local_cert_path = os.path.join(certs_dir, cert_filename)
        
        log(f"📋 Copying {cert_filename}...")
        
        # Step 1: Copy from pod to cluster host
        if cluster_host == deployer_host:
            # If deployer is also cluster host, copy directly
            copy_cmd = f"kubectl cp {kafka_namespace}/{kafka_pod_name}:{ssl_path}/{cert_filename} {remote_tmp}"
            result = execute_ssh_command(deployer_host, username, copy_cmd, password)
            
            if result is None or "error" not in result.lower():
                # Copy from deployer to local
                scp_cmd = f"scp -o StrictHostKeyChecking=no {username}@{deployer_host}:{remote_tmp} {local_cert_path}"
                if password:
                    scp_cmd = f"sshpass -p '{password}' {scp_cmd}"
                
                scp_result = subprocess.getoutput(scp_cmd)
                
                # Clean up temp file
                execute_ssh_command(deployer_host, username, f"rm -f {remote_tmp}", password)
        else:
            # Two-hop copy: pod -> cluster -> deployer -> local
            # Step 1: Copy from pod to cluster host
            copy_cmd = f"kubectl cp {kafka_namespace}/{kafka_pod_name}:{ssl_path}/{cert_filename} {remote_tmp}"
            ssh_cmd = f"ssh -o StrictHostKeyChecking=no {cluster_host} '{copy_cmd}'"
            result = execute_ssh_command(deployer_host, username, ssh_cmd, password)
            
            if result is None or "error" not in result.lower():
                # Step 2: Copy from cluster host to deployer host
                scp_cluster_to_deployer = f"scp -o StrictHostKeyChecking=no {cluster_host}:{remote_tmp} {remote_tmp}"
                execute_ssh_command(deployer_host, username, scp_cluster_to_deployer, password)
                
                # Step 3: Copy from deployer host to local
                scp_cmd = f"scp -o StrictHostKeyChecking=no {username}@{deployer_host}:{remote_tmp} {local_cert_path}"
                if password:
                    scp_cmd = f"sshpass -p '{password}' {scp_cmd}"
                
                scp_result = subprocess.getoutput(scp_cmd)
                
                # Clean up temp files on both hosts
                execute_ssh_command(deployer_host, username, f"rm -f {remote_tmp}", password)
                ssh_cleanup = f"ssh -o StrictHostKeyChecking=no {cluster_host} 'rm -f {remote_tmp}'"
                execute_ssh_command(deployer_host, username, ssh_cleanup, password)
        
        # Check if file was successfully copied
        if os.path.exists(local_cert_path) and os.path.getsize(local_cert_path) > 0:
            log(f"✅ Successfully copied: {cert_filename} ({os.path.getsize(local_cert_path)} bytes)")
            copied_files.append(cert_filename)
        else:
            log(f"⚠️  Failed to copy: {cert_filename}")
    
    # Summary of copied files
    if copied_files:
        log(f"\n📊 Successfully copied {len(copied_files)} certificate files:")
        for f in copied_files:
            log(f"   ✓ {f}")
    else:
        log("⚠️  Could not copy any certificates from Kafka pod, trying alternative method...")
    if cluster_host == deployer_host:
        def run_kubectl(cmd):
            return execute_ssh_command(cluster_host, username, cmd, password)
    else:
        def run_kubectl(cmd):
            ssh_cmd = f"ssh -o BatchMode=yes -o StrictHostKeyChecking=no {cluster_host} '{cmd}'"
            return execute_ssh_command(deployer_host, username, ssh_cmd, password)

    # Example: kubectl get secret kafka-cert -n kafka-namespace -o jsonpath='{.data}'
    certificate_secret_cmd = f"kubectl get secret kafka-cert -n {kafka_namespace} -o json"  # Changed to get whole secret as JSON
    secret_result = run_kubectl(certificate_secret_cmd)

    # Decode and save certificates
    if secret_result:
        try:
            secret_json = json.loads(secret_result)
            cert_data = base64.b64decode(secret_json['data']['CERT']).decode('utf-8')
            ca_data = base64.b64decode(secret_json['data']['CA']).decode('utf-8')

            log("✅ Writing certificates to disk...")
            with open(cert_file, 'w') as f:
                f.write(cert_data)
            with open(ca_file, 'w') as f:
                f.write(ca_data)

            log(f"✅ SSL certificates stored in {certs_dir}")
        except (json.JSONDecodeError, KeyError) as e:
            log(f"❌ Failed to parse certificates from secret: {e}")
            # Try alternative approach - look for common Kafka TLS secrets
            log("🔍 Trying alternative certificate sources...")
            extract_certificates_alternative(cluster_host, deployer_host, username, password, kafka_namespace, certs_dir)
    else:
        log("❌ Failed to fetch SSL certificates from secret")
        log("🔍 Trying alternative certificate sources...")
        extract_certificates_alternative(cluster_host, deployer_host, username, password, kafka_namespace, certs_dir)

def extract_certificates_alternative(cluster_host, deployer_host, username, password, kafka_namespace, certs_dir):
    """Alternative method to extract certificates from various sources"""
    log("🔍 Trying alternative certificate extraction methods...")
    
    # Determine SSH method
    if cluster_host == deployer_host:
        def run_kubectl(cmd):
            return execute_ssh_command(cluster_host, username, cmd, password)
    else:
        def run_kubectl(cmd):
            ssh_cmd = f"ssh -o BatchMode=yes -o StrictHostKeyChecking=no {cluster_host} '{cmd}'"
            return execute_ssh_command(deployer_host, username, ssh_cmd, password)
    
    # List all secrets in the namespace to find certificate-related ones
    secrets_cmd = f"kubectl get secrets -n {kafka_namespace} --no-headers"
    secrets_result = run_kubectl(secrets_cmd)
    
    if secrets_result:
        if DEBUG:
            log("📋 Available secrets in namespace:")
        cert_secrets = []
        for line in secrets_result.split('\n'):
            if line.strip():
                secret_name = line.split()[0]
                if DEBUG:
                    log(f"  - {secret_name}")
                if any(keyword in secret_name.lower() for keyword in ['cert', 'tls', 'ssl', 'ca']):
                    cert_secrets.append(secret_name)
        
        # Try each certificate secret
        for secret_name in cert_secrets:
            log(f"🔍 Trying to extract certificates from secret: {secret_name}")
            cert_cmd = f"kubectl get secret {secret_name} -n {kafka_namespace} -o json"
            cert_result = run_kubectl(cert_cmd)
            
            if cert_result:
                try:
                    cert_json = json.loads(cert_result)
                    data = cert_json.get('data', {})
                    
                    # Look for common certificate key names
                    ca_keys = ['ca.crt', 'ca-cert.pem', 'CA', 'ca.pem']
                    cert_keys = ['tls.crt', 'client.crt', 'cert.pem', 'CERT', 'client-cert.pem']
                    key_keys = ['tls.key', 'client.key', 'key.pem', 'KEY', 'client-key.pem']
                    
                    # Extract CA certificate
                    for ca_key in ca_keys:
                        if ca_key in data:
                            ca_data = base64.b64decode(data[ca_key]).decode('utf-8')
                            ca_file = os.path.join(certs_dir, 'ca_cert.pem')
                            with open(ca_file, 'w') as f:
                                f.write(ca_data)
                            log(f"✅ Extracted CA certificate from {secret_name}:{ca_key}")
                            break
                    
                    # Extract client certificate
                    for cert_key in cert_keys:
                        if cert_key in data:
                            cert_data = base64.b64decode(data[cert_key]).decode('utf-8')
                            cert_file = os.path.join(certs_dir, 'client-cert.pem')
                            with open(cert_file, 'w') as f:
                                f.write(cert_data)
                            log(f"✅ Extracted client certificate from {secret_name}:{cert_key}")
                            break
                    
                    # Extract client key
                    for key_key in key_keys:
                        if key_key in data:
                            key_data = base64.b64decode(data[key_key]).decode('utf-8')
                            key_file = os.path.join(certs_dir, 'client-key.pem')
                            with open(key_file, 'w') as f:
                                f.write(key_data)
                            log(f"✅ Extracted client key from {secret_name}:{key_key}")
                            break
                    
                    # If we found at least CA cert, consider it a success
                    if os.path.exists(os.path.join(certs_dir, 'ca-cert.pem')):
                        log(f"✅ Successfully extracted certificates from {secret_name}")
                        return
                        
                except (json.JSONDecodeError, KeyError) as e:
                    log(f"⚠️  Failed to parse secret {secret_name}: {e}")
                    continue
    
    # If no secrets worked, create dummy certificates as fallback
    log("⚠️  Could not extract certificates from secrets, creating self-signed certificates...")
    create_self_signed_certificates(certs_dir)

def create_self_signed_certificates(certs_dir):
    """Create self-signed certificates as fallback"""
    log("🔒 Creating self-signed certificates...")
    
    ca_file = os.path.join(certs_dir, 'ca-cert.pem')
    cert_file = os.path.join(certs_dir, 'client-cert.pem')
    key_file = os.path.join(certs_dir, 'client-key.pem')
    
    # Create a simple self-signed CA
    ca_cmd = f'openssl req -new -x509 -keyout {ca_file} -out {ca_file} -days 365 -nodes -subj "/CN=NSP-CA/OU=NSP/O=Company"'
    os.system(ca_cmd)
    
    # The client key was already created in handle_ssl_certificates
    if not os.path.exists(key_file):
        key_cmd = f'openssl genrsa -out {key_file} 2048'
        os.system(key_cmd)
    
    # Create client certificate using the existing key
    cert_cmd = f'openssl req -new -key {key_file} -out /tmp/client.csr -subj "/CN=client/OU=NSP/O=Company" && openssl x509 -req -in /tmp/client.csr -CA {ca_file} -CAkey {ca_file} -CAcreateserial -out {cert_file} -days 365'
    os.system(cert_cmd)
    
    log(f"✅ Created self-signed certificates in {certs_dir}")
    log("⚠️  Note: Self-signed certificates may not work with all Kafka configurations")


def setup_token_refresh_cron():
    """Suggest and configure cron job to refresh NSP token"""
    log("🔄 NSP Token Refresh Configuration")
    log("" + "="*50)
    log("NSP tokens expire after a period of time. You have two options:")
    log("")
    log("1. AUTOMATIC (Recommended): Set up a cron job to refresh the token every 30 minutes")
    log("2. MANUAL: Run the token refresh script manually when needed")
    log("")
    
    # Get current directory and Python executable
    current_dir = os.getcwd()
    python_executable = sys.executable
    
    # Build the cron command dynamically
    cron_schedule = "*/30 * * * *"  # Every 30 minutes
    cron_command = f"{cron_schedule} cd {current_dir} && {python_executable} nsp_token_manager.py >> nsp_token_manager.log 2>&1"
    
    choice = input("\nWould you like to set up automatic token refresh? [Y/n]: ").strip().lower()
    
    if choice != 'n':
        # Try to set up the cron job
        try:
            # Get existing crontab
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            if result.returncode == 0:
                existing_crontab = result.stdout
            else:
                existing_crontab = ""
            
            # Check if our cron job already exists
            if 'nsp_token_manager.py' in existing_crontab:
                log("✅ A cron job for token refresh already exists")
                log("📋 Existing cron entries for NSP:")
                for line in existing_crontab.split('\n'):
                    if 'nsp_token_manager.py' in line:
                        log(f"   {line}")
            else:
                # Add new cron job
                new_crontab = existing_crontab.rstrip('\n') + '\n' if existing_crontab else ''
                new_crontab += f"# NSP Token Auto-refresh\n{cron_command}\n"
                
                # Install new crontab
                process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
                process.communicate(input=new_crontab)
                
                if process.returncode == 0:
                    log("✅ Cron job successfully installed!")
                    log(f"📋 Added cron job: {cron_command}")
                    log("")
                    log("The token will be automatically refreshed every 30 minutes.")
                    log("You can check the refresh logs in: nsp_token_manager.log")
                else:
                    log("❌ Failed to install cron job")
                    show_manual_setup_instructions(cron_command)
                    
        except Exception as e:
            log(f"❌ Error setting up cron: {e}")
            show_manual_setup_instructions(cron_command)
    else:
        log("")
        log("⚠️  Manual Token Management Selected")
        log("" + "="*50)
        log("You will need to manually refresh the token before it expires.")
        log("")
        log("To refresh the token manually, run:")
        log(f"   cd {current_dir}")
        log(f"   {python_executable} nsp_token_manager.py")
        log("")
        log("The token typically expires after 1-2 hours of inactivity.")
        log("If the consumer fails with authentication errors, run the above command.")

def show_manual_setup_instructions(cron_command):
    """Show manual cron setup instructions"""
    log("")
    log("📝 To manually set up the cron job, run:")
    log("   crontab -e")
    log("")
    log("Then add this line:")
    log(f"   {cron_command}")
    log("")
    log("Save and exit the editor to activate the cron job.")

def generate_initial_token():
    """Generate initial access token and update the configuration file"""
    try:
        # Import the token manager module
        import nsp_token_manager
        
        log("🔐 Requesting initial access token...")
        
        # Get a valid token using the token manager
        server, token = nsp_token_manager.get_valid_token()
        
        if token:
            log(f"✅ Successfully obtained initial token: {token[:20]}...")
            
            # Read the current config to verify it was updated
            config = configparser.ConfigParser()
            config.read(CONFIG_FILE)
            
            # Check if token was saved
            saved_token = config.get('NSP', 'access_token', fallback='')
            if saved_token:
                log("✅ Token successfully saved to configuration file")
                return True
            else:
                log("⚠️  Token obtained but not saved to configuration")
                return False
        else:
            log("❌ Failed to obtain initial token")
            return False
            
    except Exception as e:
        log(f"❌ Error generating initial token: {e}")
        return False

def generate_config_files(config_data):
    """Generate final configuration files based on example template"""
    log("🔍 Generating configuration files...")

    # Load existing example
    config = configparser.ConfigParser()
    config.read('nsp_config.ini.example')

    # Fill in NSP section - use same field names as the example
    config['NSP']['server'] = config_data.get('nsp_ui_ip', '')
    config['NSP']['user'] = config_data.get('nsp_username', '')  # Changed from 'username' to 'user' to match example
    config['NSP']['password'] = config_data.get('nsp_password', '')  # Be cautious with storage

    # Fill in KAFKA section - bootstrap servers = NSP UI IP (VIP) as per Nokia docs
    config['KAFKA']['bootstrap_servers'] = f"{config_data.get('nsp_ui_ip', '')}:9192"

    # Add discovery info if the section doesn't exist
    if 'DISCOVERY' not in config:
        config.add_section('DISCOVERY')
    config['DISCOVERY']['namespaces_found'] = str(len(config_data.get('discovery_results', {}).get('kafka_pods', [])))
    config['DISCOVERY']['kafka_services_found'] = str(len(config_data.get('discovery_results', {}).get('kafka_pods', [])))
    config['DISCOVERY']['deployer_host'] = config_data.get('deployer_host', '')
    config['DISCOVERY']['cluster_host'] = config_data.get('cluster_host', '')

    # Write to new config
    with open(CONFIG_FILE, 'w') as f:
        config.write(f)
    
    log(f"✅ Configuration written to {CONFIG_FILE}")

def main():
    """Main execution flow"""
    log("🚀 NSP Intelligent Discovery Script v3.0 Started")
    
    try:
        # Phase 1: Connect to deployer host
        log("🔍 Phase 1: Connecting to NSP Deployer Host")
        deployer_host, username, password = get_deployer_connection()
        
        if not deployer_host:
            log("❌ Failed to connect to deployer host")
            return
        
        # Phase 2: Find cluster hosts from k8s-deployer.yml
        log("🔍 Phase 2: Finding NSP Cluster Hosts")
        cluster_hosts = find_cluster_hosts_from_deployer(deployer_host, username, password)
        
        if not cluster_hosts:
            log("⚠️  No cluster hosts found, using deployer as cluster host")
            cluster_host = deployer_host
        else:
            cluster_host = find_working_cluster_host(cluster_hosts, deployer_host, username, password)
            if not cluster_host:
                log("⚠️  No working cluster host found, using deployer as fallback")
                cluster_host = deployer_host
        
        log(f"✅ Using cluster host: {cluster_host}")
        
        # Phase 3: Discover Kafka pods directly
        log("🔍 Phase 3: Finding Kafka Pods")
        discovery_results = discover_kafka_pods(cluster_host, deployer_host, username, password)
        
        # Phase 4: Get NSP UI credentials
        log("🔍 Phase 4: NSP UI Authentication")
        suggested_ip = discovery_results.get('ingress_ip')
        nsp_ui_ip, nsp_username, nsp_password, auth_token = get_nsp_ui_credentials(suggested_ip)
        
        if not auth_token:
            log("❌ Failed to authenticate with NSP UI")
            return
        
        # Phase 5: Discover Kafka configuration
        log("🔍 Phase 5: Kafka Configuration")
        kafka_config = discover_kafka_config(cluster_host, deployer_host, username, password, discovery_results)
        
        # Phase 6: Handle SSL certificates
        log("🔍 Phase 6: SSL Certificates")
        main_kafka = discovery_results.get('main_kafka')
        if main_kafka:
            handle_ssl_certificates(cluster_host, deployer_host, username, password, main_kafka['namespace'], main_kafka['pod_name'])
        else:
            log("⚠️  Skipping SSL certificate download - no main Kafka pod found")
        
        # Phase 7: Generate configuration
        log("🔍 Phase 7: Generate Configuration")
        config_data = {
            'deployer_host': deployer_host,
            'cluster_host': cluster_host,
            'nsp_ui_ip': nsp_ui_ip,
            'nsp_username': nsp_username,
            'nsp_password': nsp_password,
            'auth_token': auth_token,
            'kafka_config': kafka_config,
            'discovery_results': discovery_results
        }
        
        generate_config_files(config_data)
        
        # Phase 8: Generate initial token and update configuration
        log("🔍 Phase 8: Generate Initial Access Token")
        if generate_initial_token():
            log("✅ Initial token generated and saved to configuration")
        else:
            log("⚠️  Could not generate initial token - you may need to run the consumer manually first")
        
        # Phase 9: Set up automatic token refresh (cron)
        log("🔍 Phase 9: Automatic Token Refresh Setup")
        setup_token_refresh_cron()
        
        log("✅ NSP Consumer setup completed successfully!")
        log("🎉 You can now run the NSP Kafka Consumer")
        
    except KeyboardInterrupt:
        log("🚫 Setup cancelled by user")
    except Exception as e:
        log(f"❌ Setup failed: {e}")
        import traceback
        log(f"Error details: {traceback.format_exc()}")

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='NSP Intelligent Discovery Script v3.0')
    parser.add_argument('--debug', '-d', action='store_true', 
                        help='Enable debug output (shows all secrets in namespace)')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='Minimal output mode')
    args = parser.parse_args()
    
    # Set global flags based on arguments
    if args.debug:
        DEBUG = True
    if args.quiet:
        VERBOSE = False
    
    main()
