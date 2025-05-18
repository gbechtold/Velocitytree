"""Response caching for Claude integration."""

import time
import json
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
import hashlib
import threading

from ..utils import logger


@dataclass
class CacheEntry:
    """Single cache entry."""
    key: str
    value: str
    timestamp: float
    hit_count: int = 0
    last_accessed: float = None
    metadata: Dict[str, Any] = None


class ResponseCache:
    """Intelligent cache for Claude responses."""
    
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        ttl: int = 3600,
        max_size: int = 1000,
        persist: bool = True
    ):
        """Initialize response cache.
        
        Args:
            cache_dir: Directory for persistent cache
            ttl: Time to live in seconds
            max_size: Maximum cache entries
            persist: Whether to persist cache to disk
        """
        self.cache_dir = cache_dir or Path.home() / ".velocitytree" / "claude_cache"
        self.ttl = ttl
        self.max_size = max_size
        self.persist = persist
        
        # In-memory cache
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.Lock()
        
        # Statistics
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0
        }
        
        # Load persistent cache
        if self.persist:
            self._load_cache()
    
    def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        with self._lock:
            # Check if key exists
            if key not in self._cache:
                self._stats["misses"] += 1
                return None
            
            entry = self._cache[key]
            
            # Check if expired
            if self._is_expired(entry):
                del self._cache[key]
                self._stats["expirations"] += 1
                self._stats["misses"] += 1
                return None
            
            # Update access info
            entry.hit_count += 1
            entry.last_accessed = time.time()
            self._stats["hits"] += 1
            
            return entry.value
    
    def set(self, key: str, value: str, metadata: Optional[Dict[str, Any]] = None):
        """Set value in cache."""
        with self._lock:
            # Check size limit
            if len(self._cache) >= self.max_size:
                self._evict_oldest()
            
            # Create entry
            entry = CacheEntry(
                key=key,
                value=value,
                timestamp=time.time(),
                last_accessed=time.time(),
                metadata=metadata or {}
            )
            
            self._cache[key] = entry
            
            # Persist if enabled
            if self.persist:
                self._save_entry(entry)
    
    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                
                # Remove from persistent storage
                if self.persist:
                    entry_file = self._get_entry_path(key)
                    if entry_file.exists():
                        entry_file.unlink()
                
                return True
            return False
    
    def clear(self):
        """Clear entire cache."""
        with self._lock:
            self._cache.clear()
            self._stats = {
                "hits": 0,
                "misses": 0,
                "evictions": 0,
                "expirations": 0
            }
            
            # Clear persistent storage
            if self.persist and self.cache_dir.exists():
                for entry_file in self.cache_dir.glob("*.json"):
                    entry_file.unlink()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0
            
            return {
                **self._stats,
                "size": len(self._cache),
                "hit_rate": hit_rate,
                "total_requests": total_requests
            }
    
    def prune(self):
        """Remove expired entries."""
        with self._lock:
            expired_keys = []
            
            for key, entry in self._cache.items():
                if self._is_expired(entry):
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
                self._stats["expirations"] += 1
                
                # Remove from persistent storage
                if self.persist:
                    entry_file = self._get_entry_path(key)
                    if entry_file.exists():
                        entry_file.unlink()
            
            logger.info(f"Pruned {len(expired_keys)} expired entries")
    
    def save(self):
        """Save cache to disk."""
        if not self.persist:
            return
        
        with self._lock:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Save metadata
            metadata_file = self.cache_dir / "metadata.json"
            metadata = {
                "stats": self._stats,
                "ttl": self.ttl,
                "max_size": self.max_size,
                "saved_at": time.time()
            }
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Save entries
            for entry in self._cache.values():
                self._save_entry(entry)
    
    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if entry is expired."""
        age = time.time() - entry.timestamp
        return age > self.ttl
    
    def _evict_oldest(self):
        """Evict oldest entry to make room."""
        if not self._cache:
            return
        
        # Find least recently used
        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].last_accessed or self._cache[k].timestamp
        )
        
        del self._cache[oldest_key]
        self._stats["evictions"] += 1
        
        # Remove from persistent storage
        if self.persist:
            entry_file = self._get_entry_path(oldest_key)
            if entry_file.exists():
                entry_file.unlink()
    
    def _get_entry_path(self, key: str) -> Path:
        """Get file path for cache entry."""
        # Create safe filename from key
        safe_key = hashlib.sha256(key.encode()).hexdigest()[:16]
        return self.cache_dir / f"{safe_key}.json"
    
    def _save_entry(self, entry: CacheEntry):
        """Save single entry to disk."""
        if not self.persist:
            return
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        entry_file = self._get_entry_path(entry.key)
        
        # Convert to dict for JSON serialization
        entry_dict = asdict(entry)
        
        with open(entry_file, 'w') as f:
            json.dump(entry_dict, f, indent=2)
    
    def _load_cache(self):
        """Load cache from disk."""
        if not self.cache_dir.exists():
            return
        
        # Load metadata
        metadata_file = self.cache_dir / "metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                self._stats = metadata.get("stats", self._stats)
            except Exception as e:
                logger.warning(f"Failed to load cache metadata: {e}")
        
        # Load entries
        loaded = 0
        for entry_file in self.cache_dir.glob("*.json"):
            if entry_file.name == "metadata.json":
                continue
            
            try:
                with open(entry_file, 'r') as f:
                    entry_dict = json.load(f)
                
                entry = CacheEntry(**entry_dict)
                
                # Skip expired entries
                if not self._is_expired(entry):
                    self._cache[entry.key] = entry
                    loaded += 1
                else:
                    entry_file.unlink()  # Clean up expired entry
                    
            except Exception as e:
                logger.warning(f"Failed to load cache entry {entry_file}: {e}")
        
        logger.info(f"Loaded {loaded} cache entries")
    
    def __len__(self) -> int:
        """Get number of cached entries."""
        return len(self._cache)
    
    def __contains__(self, key: str) -> bool:
        """Check if key is in cache."""
        with self._lock:
            if key not in self._cache:
                return False
            
            entry = self._cache[key]
            return not self._is_expired(entry)


class SmartCache(ResponseCache):
    """Enhanced cache with intelligent features."""
    
    def __init__(self, **kwargs):
        """Initialize smart cache."""
        super().__init__(**kwargs)
        self._patterns = {}  # Pattern-based caching rules
        self._priorities = {}  # Priority levels for entries
    
    def set_with_priority(
        self,
        key: str,
        value: str,
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Set value with priority level."""
        self.set(key, value, metadata)
        self._priorities[key] = priority
    
    def add_pattern_rule(self, pattern: str, ttl_override: Optional[int] = None):
        """Add caching rule based on key pattern."""
        self._patterns[pattern] = {
            "ttl_override": ttl_override
        }
    
    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check expiration with pattern rules."""
        # Check pattern-based TTL overrides
        for pattern, rule in self._patterns.items():
            if pattern in entry.key and rule["ttl_override"]:
                age = time.time() - entry.timestamp
                return age > rule["ttl_override"]
        
        return super()._is_expired(entry)
    
    def _evict_oldest(self):
        """Evict based on priority and age."""
        if not self._cache:
            return
        
        # Sort by priority (lower is less important) and age
        candidates = []
        for key, entry in self._cache.items():
            priority = self._priorities.get(key, 0)
            age = time.time() - (entry.last_accessed or entry.timestamp)
            score = priority - (age / 3600)  # Reduce score by age in hours
            candidates.append((key, score))
        
        # Evict lowest scoring entry
        candidates.sort(key=lambda x: x[1])
        evict_key = candidates[0][0]
        
        del self._cache[evict_key]
        if evict_key in self._priorities:
            del self._priorities[evict_key]
        
        self._stats["evictions"] += 1
        
        # Remove from persistent storage
        if self.persist:
            entry_file = self._get_entry_path(evict_key)
            if entry_file.exists():
                entry_file.unlink()
    
    def get_by_pattern(self, pattern: str) -> Dict[str, str]:
        """Get all entries matching a pattern."""
        results = {}
        
        with self._lock:
            for key, entry in self._cache.items():
                if pattern in key and not self._is_expired(entry):
                    results[key] = entry.value
        
        return results
    
    def analyze_usage(self) -> Dict[str, Any]:
        """Analyze cache usage patterns."""
        analysis = {
            "most_accessed": [],
            "least_accessed": [],
            "oldest_entries": [],
            "largest_values": [],
            "patterns": {}
        }
        
        with self._lock:
            # Sort by access count
            by_access = sorted(
                self._cache.items(),
                key=lambda x: x[1].hit_count,
                reverse=True
            )
            
            analysis["most_accessed"] = [
                {"key": k, "hits": v.hit_count}
                for k, v in by_access[:5]
            ]
            
            analysis["least_accessed"] = [
                {"key": k, "hits": v.hit_count}
                for k, v in by_access[-5:]
            ]
            
            # Sort by age
            by_age = sorted(
                self._cache.items(),
                key=lambda x: x[1].timestamp
            )
            
            analysis["oldest_entries"] = [
                {"key": k, "age": time.time() - v.timestamp}
                for k, v in by_age[:5]
            ]
            
            # Sort by value size
            by_size = sorted(
                self._cache.items(),
                key=lambda x: len(x[1].value),
                reverse=True
            )
            
            analysis["largest_values"] = [
                {"key": k, "size": len(v.value)}
                for k, v in by_size[:5]
            ]
            
            # Analyze patterns
            for pattern in self._patterns:
                matches = sum(1 for k in self._cache if pattern in k)
                analysis["patterns"][pattern] = matches
        
        return analysis