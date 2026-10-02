import app.models as canonical_models
import app.risk as canonical_risk
import models as runtime_models
import risk as runtime_risk


def test_runtime_models_are_canonical_exports():
    assert runtime_models.RiskSettings is canonical_models.RiskSettings
    assert runtime_models.TradePlan is canonical_models.TradePlan


def test_runtime_risk_engine_is_canonical_export():
    assert runtime_risk.RiskError is canonical_risk.RiskError
    assert runtime_risk.position_size is canonical_risk.position_size
    assert runtime_risk.validate is canonical_risk.validate


def test_runtime_risk_settings_use_centralized_configuration():
    settings = runtime_models.RiskSettings()

    assert settings.risk_per_trade == canonical_models.settings.risk_per_trade
    assert settings.daily_loss_limit == canonical_models.settings.daily_loss_limit
    assert settings.max_total_exposure == canonical_models.settings.max_total_exposure
    assert settings.max_positions == canonical_models.settings.max_open_positions
