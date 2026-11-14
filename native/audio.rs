/// Measures mono PCM energy for the wake gate. The caller owns the buffer.
#[no_mangle]
pub unsafe extern "C" fn jarvis_pcm_rms(samples: *const f32, length: usize) -> f32 {
    if samples.is_null() || length == 0 {
        return 0.0;
    }
    let pcm = unsafe { std::slice::from_raw_parts(samples, length) };
    (pcm.iter().map(|sample| sample * sample).sum::<f32>() / length as f32).sqrt()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn measures_signal_energy() {
        let pcm = [0.5, -0.5, 0.5, -0.5];
        assert_eq!(unsafe { jarvis_pcm_rms(pcm.as_ptr(), pcm.len()) }, 0.5);
        assert_eq!(unsafe { jarvis_pcm_rms(std::ptr::null(), 0) }, 0.0);
    }
}
