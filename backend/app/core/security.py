from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from .config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str, token_type: str = "access") -> dict:
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)

from cryptography.fernet import Fernet
import json
import base64

class EncryptionService:
    """Service for encrypting/decrypting sensitive data"""
    
    def __init__(self):
        # Ensure key is properly formatted for Fernet
        key_bytes = settings.ENCRYPTION_KEY.encode()
        if len(key_bytes) != 44:  # Fernet key must be 44 bytes base64
            # Pad or truncate key to proper length
            key_bytes = (key_bytes + b'=' * 44)[:44]
        try:
            # Ensure key is valid base64
            base64.urlsafe_b64decode(key_bytes)
            self.key = key_bytes
        except:
            # If invalid, create a new key (in production, this should be handled properly)
            self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)
    
    def encrypt_data(self, data: Union[str, dict]) -> str:
        """Encrypt sensitive data"""
        if isinstance(data, dict):
            data = json.dumps(data)
        data_bytes = data.encode()
        encrypted = self.cipher.encrypt(data_bytes)
        return encrypted.decode()
    
    def decrypt_data(self, encrypted_data: str) -> Union[str, dict]:
        """Decrypt sensitive data"""
        decrypted = self.cipher.decrypt(encrypted_data.encode())
        decrypted_str = decrypted.decode()
        
        # Try to parse as JSON first
        try:
            return json.loads(decrypted_str)
        except:
            return decrypted_str

encryption_service = EncryptionService()
