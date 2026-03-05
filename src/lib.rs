use std::panic;
use console_error_panic_hook;
use wasm_bindgen::prelude::*;
use wasm_bindgen::closure::Closure;

#[wasm_bindgen(start)]
pub fn init() {
    panic::set_hook(Box::new(console_error_panic_hook::hook));
}

#[wasm_bindgen]
pub fn create_button() -> Result<(), JsValue> {
    let window = web_sys::window().unwrap();
    let document = window.document().unwrap();
    let body = document.body().unwrap();

    let button = document.create_element("button")?;
    button.set_text_content(Some("Click Me!"));
    
    let closure = Closure::<dyn Fn()>::new(|| {
        web_sys::console::log_1(&"Button clicked!".into());
    });
    
    button.add_event_listener_with_callback("click", closure.as_ref().unchecked_ref())?;
    closure.forget(); // Proper memory management
    
    body.append_child(&button)?;
    Ok(())
}