def predict_dynamic_conf(model, source, start_conf=0.50, min_conf=0.05, step=0.05,
                         iou=0.45, imgsz=640, device="0", half=False, save=False):
    current_conf = round(start_conf, 4)
    last_result = None
    while current_conf >= min_conf - 1e-9:
        results = model.predict(
            source=source,
            conf=current_conf,
            iou=iou,
            imgsz=imgsz,
            device=device,
            half=half,
            save=save,
            verbose=False,
        )
        last_result = results[0]
        if last_result.boxes is not None and len(last_result.boxes) > 0:
            return last_result, current_conf
        current_conf = round(current_conf - step, 4)
    return last_result, 0.0
