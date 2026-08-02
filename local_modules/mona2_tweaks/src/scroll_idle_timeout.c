/*
 * SCROLLレイヤー(トグル式)の無操作自動解除。
 *
 * 挙動:
 *   - 対象レイヤーがアクティブになった瞬間にタイマー開始 (入力を待たない)
 *   - キー押下(position)・エンコーダー(sensor)・トラックボール等(Zephyr input)の
 *     いずれの操作でもタイマーをリセット
 *   - タイムアウトまで完全に無操作ならレイヤーを自動解除
 *   - &tog等による手動解除は従来通り (解除時にタイマーは破棄される)
 *
 * input processor (zip_temp_layer) では「入力イベント通過時しか動けない」ため
 * この挙動を実現できず、常駐リスナーとして実装している。
 */

#include <zephyr/kernel.h>
#include <zephyr/input/input.h>

#include <zmk/event_manager.h>
#include <zmk/events/layer_state_changed.h>
#include <zmk/events/position_state_changed.h>
#include <zmk/events/sensor_event.h>
#include <zmk/keymap.h>

#define IDLE_LAYER CONFIG_MONA2_SCROLL_IDLE_TIMEOUT_LAYER
#define IDLE_TIMEOUT_MS CONFIG_MONA2_SCROLL_IDLE_TIMEOUT_MS

static void idle_deactivate_cb(struct k_work *work) {
    ARG_UNUSED(work);
    if (zmk_keymap_layer_active(IDLE_LAYER)) {
        zmk_keymap_layer_deactivate(IDLE_LAYER);
    }
}

static K_WORK_DELAYABLE_DEFINE(idle_work, idle_deactivate_cb);

/* 対象レイヤーがアクティブな間だけタイマーを延長する (ISRからも呼ばれ得るが両APIともISR安全) */
static void idle_refresh(void) {
    if (zmk_keymap_layer_active(IDLE_LAYER)) {
        k_work_reschedule(&idle_work, K_MSEC(IDLE_TIMEOUT_MS));
    }
}

/* トラックボール等、Zephyr inputサブシステム全デバイスの生イベント (dev=NULLで全デバイス購読) */
static void idle_input_cb(struct input_event *evt) {
    ARG_UNUSED(evt);
    idle_refresh();
}
INPUT_CALLBACK_DEFINE(NULL, idle_input_cb);

static int idle_event_listener(const zmk_event_t *eh) {
    const struct zmk_layer_state_changed *lev = as_zmk_layer_state_changed(eh);
    if (lev != NULL) {
        if (lev->layer == IDLE_LAYER) {
            if (lev->state) {
                k_work_reschedule(&idle_work, K_MSEC(IDLE_TIMEOUT_MS));
            } else {
                k_work_cancel_delayable(&idle_work);
            }
        }
        return ZMK_EV_EVENT_BUBBLE;
    }

    /* position (両手のキー押下) / sensor (エンコーダー) はここに来る */
    idle_refresh();
    return ZMK_EV_EVENT_BUBBLE;
}

ZMK_LISTENER(mona2_scroll_idle, idle_event_listener);
ZMK_SUBSCRIPTION(mona2_scroll_idle, zmk_layer_state_changed);
ZMK_SUBSCRIPTION(mona2_scroll_idle, zmk_position_state_changed);
ZMK_SUBSCRIPTION(mona2_scroll_idle, zmk_sensor_event);
