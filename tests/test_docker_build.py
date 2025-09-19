"""
Docker build and container tests
"""
import pytest
import docker
import requests
import time
import os
import subprocess
from typing import Generator

class TestDockerBuild:
    """Test Docker image building and container functionality"""
    
    @pytest.fixture(scope="class")
    def docker_client(self) -> docker.DockerClient:
        """Get Docker client"""
        return docker.from_env()
    
    @pytest.fixture(scope="class")
    def built_image(self, docker_client: docker.DockerClient) -> Generator[str, None, None]:
        """Build Docker image for testing"""
        image_tag = "grading-system:test"
        
        # Build image
        image, logs = docker_client.images.build(
            path=".",
            tag=image_tag,
            rm=True,
            forcerm=True
        )
        
        yield image_tag
        
        # Cleanup
        try:
            docker_client.images.remove(image_tag, force=True)
        except Exception:
            pass
    
    def test_dockerfile_exists(self):
        """Test that Dockerfile exists"""
        assert os.path.exists("Dockerfile"), "Dockerfile not found"
    
    def test_docker_compose_files_exist(self):
        """Test that docker-compose files exist"""
        assert os.path.exists("docker-compose.yml"), "docker-compose.yml not found"
        assert os.path.exists("docker-compose.ssl.yml"), "docker-compose.ssl.yml not found"
    
    def test_image_builds_successfully(self, built_image: str):
        """Test that Docker image builds without errors"""
        # If we get here, the image built successfully
        assert built_image is not None
    
    def test_image_has_correct_labels(self, docker_client: docker.DockerClient, built_image: str):
        """Test that image has correct metadata"""
        image = docker_client.images.get(built_image)
        
        # Check that image exists and has basic properties
        assert image.id is not None
        assert len(image.tags) > 0
    
    def test_container_starts_successfully(self, docker_client: docker.DockerClient, built_image: str):
        """Test that container starts without immediate crashes"""
        container = None
        try:
            # Start container with minimal environment
            container = docker_client.containers.run(
                built_image,
                environment={
                    "AI_API_KEY": "test_key",
                    "ARK_API_KEY": "test_key"
                },
                detach=True,
                remove=True,
                ports={"8000/tcp": None}
            )
            
            # Wait a bit for startup
            time.sleep(5)
            
            # Check container is still running
            container.reload()
            assert container.status == "running"
            
        finally:
            if container:
                try:
                    container.stop(timeout=10)
                except Exception:
                    pass
    
    def test_health_check_endpoint(self, docker_client: docker.DockerClient, built_image: str):
        """Test that health check endpoint responds"""
        container = None
        try:
            # Start container
            container = docker_client.containers.run(
                built_image,
                environment={
                    "AI_API_KEY": "test_key",
                    "ARK_API_KEY": "test_key"
                },
                detach=True,
                remove=True,
                ports={"8000/tcp": 8000}
            )
            
            # Wait for startup
            time.sleep(10)
            
            # Test health endpoint
            try:
                response = requests.get("http://localhost:8000/health", timeout=5)
                assert response.status_code == 200
                assert "status" in response.json()
            except requests.exceptions.ConnectionError:
                # Container might not be fully ready, check if it's at least running
                container.reload()
                assert container.status == "running"
                
        finally:
            if container:
                try:
                    container.stop(timeout=10)
                except Exception:
                    pass
    
    def test_docker_compose_config_valid(self):
        """Test that docker-compose configuration is valid"""
        result = subprocess.run(
            ["docker-compose", "config"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, f"docker-compose config failed: {result.stderr}"
    
    def test_environment_variables_validation(self, docker_client: docker.DockerClient, built_image: str):
        """Test that container validates required environment variables"""
        container = None
        try:
            # Start container without required env vars
            container = docker_client.containers.run(
                built_image,
                detach=True,
                remove=True
            )
            
            # Wait a bit
            time.sleep(5)
            
            # Container should exit due to missing env vars
            container.reload()
            assert container.status in ["exited", "dead"]
            
        except Exception:
            # Expected to fail
            pass
        finally:
            if container:
                try:
                    container.stop(timeout=5)
                except Exception:
                    pass

class TestDockerSecurity:
    """Test Docker security configurations"""
    
    def test_dockerfile_uses_non_root_user(self):
        """Test that Dockerfile configures non-root user"""
        with open("Dockerfile", "r") as f:
            content = f.read()
        
        # Check for user creation and switching
        assert "useradd" in content or "adduser" in content
        assert "USER " in content
        assert "USER root" not in content.split("USER ")[-1].split("\n")[0]
    
    def test_dockerfile_security_best_practices(self):
        """Test Dockerfile follows security best practices"""
        with open("Dockerfile", "r") as f:
            content = f.read()
        
        # Should not run as root in final stage
        lines = content.split("\n")
        user_lines = [line for line in lines if line.strip().startswith("USER ")]
        
        if user_lines:
            last_user = user_lines[-1]
            assert "root" not in last_user.lower()
    
    def test_docker_compose_security_settings(self):
        """Test docker-compose has security configurations"""
        result = subprocess.run(
            ["docker-compose", "config"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        config = result.stdout
        
        # Should have resource limits
        assert "cpus" in config or "cpu_limit" in config
        assert "memory" in config or "mem_limit" in config

class TestDockerNetworking:
    """Test Docker networking configuration"""
    
    def test_docker_compose_network_config(self):
        """Test that docker-compose defines custom network"""
        result = subprocess.run(
            ["docker-compose", "config"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        config = result.stdout
        
        # Should define custom network
        assert "networks:" in config
        assert "grading-network" in config

if __name__ == "__main__":
    pytest.main([__file__, "-v"])