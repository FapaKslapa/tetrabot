mod bot;
mod cli;
mod commands;
mod engine;
mod sim;

use cli::{arg, flag};
use engine::NO_SD;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if flag(&args, "--nosd") {
        NO_SD.store(true, std::sync::atomic::Ordering::Relaxed);
    }
    let mode = args.get(1).cloned().unwrap_or_else(|| "help".into());
    let depth: usize = arg(&args, "--depth", "6").parse().unwrap_or(6);
    let width: usize = arg(&args, "--width", "120").parse().unwrap_or(120);
    match mode.as_str() {
        "serve" => commands::serve(depth, width),
        "solo" => commands::run_solo(&args, depth, width),
        "versus" => commands::run_versus(&args, depth, width),
        "check" => commands::run_check(),
        "tune" => commands::tune(&args),
        _ => println!("usage: tetrabot serve|solo|versus|check|tune [--depth N] [--width N] [--nosd]"),
    }
}
