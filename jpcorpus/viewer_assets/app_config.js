window.JPCORPUS_CONFIG = (() => {
  const SERVICE_LABEL_KEYS = {
    bangumi: "configServiceBangumi",
    jimaku: "configServiceJimaku",
    llm: "configServiceLlm",
  };

  const MISSING_LABEL_KEYS = {
    JPCORPUS_BANGUMI_CLIENT_ID: "configBangumiClientId",
    JPCORPUS_BANGUMI_CLIENT_SECRET: "configBangumiClientSecret",
    JIMAKU_API_KEY: "configJimakuApiKey",
    JPCORPUS_LLM_MODEL: "configLlmModel",
    JPCORPUS_LLM_API_KEY: "configLlmApiKey",
    OPENAI_API_KEY: "configOpenAiApiKey",
    ANTHROPIC_API_KEY: "configAnthropicApiKey",
  };

  function configServiceLabel(service, t) {
    const key = SERVICE_LABEL_KEYS[service?.id || ""];
    return key ? t(key) : service?.label || service?.id || "";
  }

  function configMissingLabels(service, t) {
    const missing = Array.isArray(service?.missing) ? service.missing : [];
    return missing.map((key) => {
      const labelKey = MISSING_LABEL_KEYS[key];
      return labelKey ? t(labelKey) : key;
    });
  }

  return {
    configMissingLabels,
    configServiceLabel,
  };
})();
