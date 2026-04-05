"""
MLflow Model Versioning Service — tracks experiments, models, and metrics.

Provides model versioning, experiment tracking, and A/B testing infrastructure
for production ML model management.
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from uuid import uuid4
import hashlib
from loguru import logger

from app.core.config import settings


class MLflowService:
    """
    Lightweight MLflow-compatible experiment tracking service.
    
    Provides:
    - Experiment management
    - Run tracking with metrics
    - Model versioning and registry
    - Artifact logging
    
    Note: This is a file-based implementation for demonstration.
    In production, replace with actual MLflow server integration.
    """
    
    STAGES = ['staging', 'production', 'archived']
    
    def __init__(self):
        self.tracking_path = Path(settings.MODEL_SAVE_PATH) / "mlflow"
        self.experiments_path = self.tracking_path / "experiments"
        self.models_path = self.tracking_path / "models"
        self.runs_path = self.tracking_path / "runs"
        
        # Create directories
        for p in [self.experiments_path, self.models_path, self.runs_path]:
            p.mkdir(parents=True, exist_ok=True)
    
    # ==================== EXPERIMENTS ====================
    
    def create_experiment(
        self,
        name: str,
        description: str = "",
        tags: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Create a new experiment."""
        experiment_id = str(uuid4())[:8]
        
        experiment = {
            'experiment_id': experiment_id,
            'name': name,
            'description': description,
            'tags': tags or {},
            'created_at': datetime.utcnow().isoformat(),
            'runs': []
        }
        
        exp_file = self.experiments_path / f"{experiment_id}.json"
        exp_file.write_text(json.dumps(experiment, indent=2))
        
        logger.info(f"Created experiment: {name} ({experiment_id})")
        
        return experiment
    
    def get_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Get experiment by ID."""
        exp_file = self.experiments_path / f"{experiment_id}.json"
        
        if exp_file.exists():
            return json.loads(exp_file.read_text())
        return None
    
    def list_experiments(self) -> List[Dict[str, Any]]:
        """List all experiments."""
        experiments = []
        
        for exp_file in self.experiments_path.glob("*.json"):
            try:
                experiments.append(json.loads(exp_file.read_text()))
            except Exception:
                continue
        
        return sorted(experiments, key=lambda x: x.get('created_at', ''), reverse=True)
    
    # ==================== RUNS ====================
    
    def start_run(
        self,
        experiment_id: str,
        run_name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Start a new run within an experiment."""
        run_id = str(uuid4())[:12]
        
        run = {
            'run_id': run_id,
            'experiment_id': experiment_id,
            'run_name': run_name or f"run-{run_id[:6]}",
            'status': 'running',
            'start_time': datetime.utcnow().isoformat(),
            'end_time': None,
            'tags': tags or {},
            'params': {},
            'metrics': {},
            'artifacts': []
        }
        
        run_file = self.runs_path / f"{run_id}.json"
        run_file.write_text(json.dumps(run, indent=2))
        
        # Update experiment
        exp = self.get_experiment(experiment_id)
        if exp:
            exp['runs'].append(run_id)
            exp_file = self.experiments_path / f"{experiment_id}.json"
            exp_file.write_text(json.dumps(exp, indent=2))
        
        logger.info(f"Started run: {run_name} ({run_id})")
        
        return run
    
    def log_params(self, run_id: str, params: Dict[str, Any]) -> None:
        """Log parameters to a run."""
        run = self._load_run(run_id)
        if run:
            run['params'].update(params)
            self._save_run(run_id, run)
    
    def log_metrics(
        self,
        run_id: str,
        metrics: Dict[str, float],
        step: Optional[int] = None
    ) -> None:
        """Log metrics to a run."""
        run = self._load_run(run_id)
        if run:
            for key, value in metrics.items():
                if key not in run['metrics']:
                    run['metrics'][key] = []
                run['metrics'][key].append({
                    'value': value,
                    'step': step,
                    'timestamp': datetime.utcnow().isoformat()
                })
            self._save_run(run_id, run)
    
    def log_artifact(
        self,
        run_id: str,
        artifact_path: str,
        artifact_type: str = "file"
    ) -> None:
        """Log an artifact to a run."""
        run = self._load_run(run_id)
        if run:
            run['artifacts'].append({
                'path': artifact_path,
                'type': artifact_type,
                'logged_at': datetime.utcnow().isoformat()
            })
            self._save_run(run_id, run)
    
    def end_run(self, run_id: str, status: str = "completed") -> Dict[str, Any]:
        """End a run."""
        run = self._load_run(run_id)
        if run:
            run['status'] = status
            run['end_time'] = datetime.utcnow().isoformat()
            self._save_run(run_id, run)
            logger.info(f"Ended run: {run_id} with status {status}")
        return run
    
    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get run by ID."""
        return self._load_run(run_id)
    
    def list_runs(
        self,
        experiment_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List runs, optionally filtered by experiment and status."""
        runs = []
        
        for run_file in self.runs_path.glob("*.json"):
            try:
                run = json.loads(run_file.read_text())
                
                if experiment_id and run.get('experiment_id') != experiment_id:
                    continue
                if status and run.get('status') != status:
                    continue
                
                runs.append(run)
            except Exception:
                continue
        
        return sorted(runs, key=lambda x: x.get('start_time', ''), reverse=True)
    
    def _load_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Load run from file."""
        run_file = self.runs_path / f"{run_id}.json"
        if run_file.exists():
            return json.loads(run_file.read_text())
        return None
    
    def _save_run(self, run_id: str, run: Dict[str, Any]) -> None:
        """Save run to file."""
        run_file = self.runs_path / f"{run_id}.json"
        run_file.write_text(json.dumps(run, indent=2))
    
    # ==================== MODEL REGISTRY ====================
    
    def register_model(
        self,
        name: str,
        run_id: str,
        model_path: str,
        description: str = "",
        tags: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Register a model in the model registry."""
        model_file = self.models_path / f"{name}.json"
        
        # Load or create model entry
        if model_file.exists():
            model = json.loads(model_file.read_text())
        else:
            model = {
                'name': name,
                'description': description,
                'created_at': datetime.utcnow().isoformat(),
                'versions': []
            }
        
        # Create new version
        version = len(model['versions']) + 1
        version_hash = hashlib.md5(f"{run_id}{model_path}".encode()).hexdigest()[:8]
        
        version_entry = {
            'version': version,
            'version_id': f"v{version}-{version_hash}",
            'run_id': run_id,
            'model_path': model_path,
            'stage': 'staging',
            'tags': tags or {},
            'registered_at': datetime.utcnow().isoformat(),
            'metrics': self._get_run_metrics(run_id)
        }
        
        model['versions'].append(version_entry)
        model['latest_version'] = version
        model['updated_at'] = datetime.utcnow().isoformat()
        
        model_file.write_text(json.dumps(model, indent=2))
        
        logger.info(f"Registered model: {name} v{version}")
        
        return version_entry
    
    def _get_run_metrics(self, run_id: str) -> Dict[str, float]:
        """Get latest metrics from a run."""
        run = self._load_run(run_id)
        if not run:
            return {}
        
        metrics = {}
        for key, values in run.get('metrics', {}).items():
            if values:
                metrics[key] = values[-1]['value']
        return metrics
    
    def get_model(self, name: str) -> Optional[Dict[str, Any]]:
        """Get model from registry."""
        model_file = self.models_path / f"{name}.json"
        if model_file.exists():
            return json.loads(model_file.read_text())
        return None
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List all registered models."""
        models = []
        
        for model_file in self.models_path.glob("*.json"):
            try:
                model = json.loads(model_file.read_text())
                models.append({
                    'name': model['name'],
                    'description': model.get('description', ''),
                    'latest_version': model.get('latest_version'),
                    'total_versions': len(model.get('versions', [])),
                    'created_at': model.get('created_at'),
                    'updated_at': model.get('updated_at')
                })
            except Exception:
                continue
        
        return sorted(models, key=lambda x: x.get('updated_at', ''), reverse=True)
    
    def transition_model_stage(
        self,
        name: str,
        version: int,
        stage: str
    ) -> Optional[Dict[str, Any]]:
        """Transition a model version to a new stage."""
        if stage not in self.STAGES:
            raise ValueError(f"Invalid stage: {stage}. Must be one of {self.STAGES}")
        
        model = self.get_model(name)
        if not model:
            return None
        
        for v in model['versions']:
            if v['version'] == version:
                old_stage = v['stage']
                v['stage'] = stage
                v['stage_updated_at'] = datetime.utcnow().isoformat()
                
                # If transitioning to production, demote current production
                if stage == 'production':
                    for other in model['versions']:
                        if other['version'] != version and other['stage'] == 'production':
                            other['stage'] = 'archived'
                            other['stage_updated_at'] = datetime.utcnow().isoformat()
                
                model_file = self.models_path / f"{name}.json"
                model_file.write_text(json.dumps(model, indent=2))
                
                logger.info(f"Model {name} v{version}: {old_stage} -> {stage}")
                
                return v
        
        return None
    
    def get_production_model(self, name: str) -> Optional[Dict[str, Any]]:
        """Get the production version of a model."""
        model = self.get_model(name)
        if not model:
            return None
        
        for v in model['versions']:
            if v['stage'] == 'production':
                return v
        
        return None
    
    def compare_versions(
        self,
        name: str,
        version1: int,
        version2: int
    ) -> Dict[str, Any]:
        """Compare metrics between two model versions."""
        model = self.get_model(name)
        if not model:
            return {'error': 'Model not found'}
        
        v1 = v2 = None
        for v in model['versions']:
            if v['version'] == version1:
                v1 = v
            if v['version'] == version2:
                v2 = v
        
        if not v1 or not v2:
            return {'error': 'One or both versions not found'}
        
        comparison = {
            'model': name,
            'version_1': {
                'version': version1,
                'stage': v1['stage'],
                'metrics': v1.get('metrics', {})
            },
            'version_2': {
                'version': version2,
                'stage': v2['stage'],
                'metrics': v2.get('metrics', {})
            },
            'differences': {}
        }
        
        # Calculate differences
        all_metrics = set(v1.get('metrics', {}).keys()) | set(v2.get('metrics', {}).keys())
        
        for metric in all_metrics:
            m1 = v1.get('metrics', {}).get(metric)
            m2 = v2.get('metrics', {}).get(metric)
            
            if m1 is not None and m2 is not None:
                diff = m2 - m1
                comparison['differences'][metric] = {
                    'v1': m1,
                    'v2': m2,
                    'diff': round(diff, 4),
                    'better': 'v2' if diff > 0 else ('v1' if diff < 0 else 'equal')
                }
        
        return comparison
    
    # ==================== EXPERIMENT TRACKING SUMMARY ====================
    
    def get_tracking_summary(self) -> Dict[str, Any]:
        """Get overall tracking summary."""
        experiments = self.list_experiments()
        runs = self.list_runs()
        models = self.list_models()
        
        return {
            'total_experiments': len(experiments),
            'total_runs': len(runs),
            'runs_by_status': {
                'running': len([r for r in runs if r.get('status') == 'running']),
                'completed': len([r for r in runs if r.get('status') == 'completed']),
                'failed': len([r for r in runs if r.get('status') == 'failed'])
            },
            'total_models': len(models),
            'production_models': sum(
                1 for m in models 
                if self.get_production_model(m['name'])
            ),
            'recent_experiments': experiments[:5],
            'recent_runs': runs[:5],
            'recent_models': models[:5]
        }


# Demo data generator
def initialize_demo_tracking():
    """Initialize demo experiments and runs."""
    service = mlflow_service
    
    # Create experiment
    exp = service.create_experiment(
        name="multi-disease-models",
        description="Training experiments for multi-disease prediction models",
        tags={"project": "dissertation", "version": "1.0"}
    )
    
    # Create some runs
    for disease in ['heart', 'diabetes', 'kidney']:
        for model_type in ['random_forest', 'xgboost']:
            run = service.start_run(
                experiment_id=exp['experiment_id'],
                run_name=f"{disease}_{model_type}",
                tags={"disease": disease, "model_type": model_type}
            )
            
            # Log params
            service.log_params(run['run_id'], {
                'disease': disease,
                'model_type': model_type,
                'n_estimators': 100,
                'max_depth': 10,
                'test_size': 0.2
            })
            
            # Log metrics (simulated)
            import random
            service.log_metrics(run['run_id'], {
                'accuracy': 0.85 + random.uniform(0, 0.1),
                'precision': 0.82 + random.uniform(0, 0.1),
                'recall': 0.80 + random.uniform(0, 0.1),
                'f1_score': 0.81 + random.uniform(0, 0.1),
                'auc_roc': 0.88 + random.uniform(0, 0.08)
            })
            
            # End run
            service.end_run(run['run_id'], status='completed')
            
            # Register model
            service.register_model(
                name=f"{disease}_model",
                run_id=run['run_id'],
                model_path=f"models/{disease}_{model_type}.joblib",
                description=f"{disease.title()} prediction model using {model_type}",
                tags={"algorithm": model_type}
            )
    
    # Promote one version to production for each disease
    for disease in ['heart', 'diabetes', 'kidney']:
        model = service.get_model(f"{disease}_model")
        if model and model.get('versions'):
            service.transition_model_stage(
                f"{disease}_model",
                version=1,
                stage='production'
            )
    
    logger.info("Demo tracking data initialized")
    return service.get_tracking_summary()


# Singleton instance
mlflow_service = MLflowService()
