if(CONFIG_MONA2_SCROLL_IDLE_TIMEOUT)
  zephyr_library_named(mona2_tweaks)
  zephyr_library_sources(src/scroll_idle_timeout.c)
endif()
