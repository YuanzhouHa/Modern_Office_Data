import random
import re
import unreal

def clean_sequencer(level_sequence):
    bindings = level_sequence.get_bindings()
    for b in bindings:
        b_display_name = str(b.get_display_name())
        if "Camera" not in  b_display_name:
            b.remove()

def select_random_asset(assets_path, asset_class=None):
    eal = unreal.EditorAssetLibrary()
    assets = eal.list_assets(assets_path)

    if asset_class is not None:
        filtered_assets = []
        for asset in assets:
            try:
                if unreal.EditorAssetLibrary.find_asset_data(asset).asset_class_path.asset_name == asset_class:
                    filtered_assets.append(asset)
            except:
                continue

        assets = filtered_assets

    selected_asset_path = random.choice(assets)

    return selected_asset_path

def spawn_actor(asset_path, location=unreal.Vector(0.0, 0.0, 0.0)):
    # spawn actor into level
    obj = unreal.load_asset(asset_path)
    rotation = unreal.Rotator(0, 0, 0)
    actor = unreal.EditorLevelLibrary.spawn_actor_from_object(object_to_use=obj,
                                                              location=location,
                                                              rotation=rotation)

    actor.set_actor_scale3d(unreal.Vector(1.0, 1.0, 1.0))
    # actor.get_editor_property('render_component').set_editor_property('cast_shadow', self.add_sprite_based_shadow)

    return actor

def add_animation_to_actor(spawnable_actor, animation_path):
    # Get the skeleton animation track class
    anim_track = spawnable_actor.add_track(unreal.MovieSceneSkeletalAnimationTrack)
    # Add a new animation section
    animation_section = anim_track.add_section()
    # Set the skeletal animation asset
    animation_asset = unreal.load_asset(animation_path)
    animation_section.params.animation = animation_asset

    # Set the Section Range
    frame_rate = 30  # level_sequence.get_frame_rate()
    start_frame = 0
    end_frame = animation_asset.get_editor_property('sequence_length') * frame_rate.numerator / frame_rate.denominator
    animation_section.set_range(start_frame, end_frame)

def find_relevant_assets(level_sequence):

    camera_re = re.compile("SuperCineCameraActor_([0-9]+)")
    target_point_re = re.compile("TargetPoint_([0-9]+)")

    cameras = {}
    target_points = {}
    # hdri_backdrop = None
    #all_actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    # ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    # current_world = ues.get_editor_world()
    # bound_objects = unreal.SequencerTools().get_bound_objects(current_world, level_sequence, level_sequence.get_bindings(), level_sequence.get_playback_range())
    # for b_obj in bound_objects:
    #     for actor1 in b_obj.bound_objects:
    #         print(actor1.get_name())
    #         if 'CineCamera' in actor1.get_name():
    #             camera = actor1
    #             break
    all_actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    for actor in all_actors:
        name = actor.get_actor_label()
        # if 'HDRIBackdrop' in actor.get_name():
        #     hdri_backdrop = actor
        camera_matches = camera_re.search(name)
        target_point_matches = target_point_re.search(name)

        if camera_matches is not None:
            cameras[camera_matches.group(1)] = actor
        if target_point_matches is not None:
            target_points[target_point_matches.group(1)] = actor

    # return camera, hdri_backdrop
    return cameras, target_points

def look_at_target(camera, target_point):
    # Get location of target point and offset
    target_location = target_point.get_actor_location() + unreal.Vector(0, 0, 110)
    camera_location = camera.get_actor_location()

    # Compute look-at rotation
    direction = target_location - camera_location
    look_at_rotation = unreal.RotationMatrix.make_from_x(direction).rotator()

    # Apply rotation to camera
    camera.set_actor_rotation(look_at_rotation)
    unreal.log(f"Camera rotated to look at {target_location}")


def bind_camera_to_sequence(level_sequence, camera_actor):
    # add camera to sequence  possessable list
    camera_binding = level_sequence.add_possessable(camera_actor)
    level_sequence.bind_possessable_object(camera_binding.get_guid(), camera_actor, unreal.EditorLevelLibrary.get_editor_world())

    # 获取 MovieScene
    movie_scene = level_sequence.get_movie_scene()

    # 添加 Camera Cut Track
    camera_cut_track = movie_scene.add_camera_cut_track()
    camera_cut_section = camera_cut_track.add_section()
    camera_cut_section.set_range(0.0, 150.0)  # 设置范围为 5 秒（30 fps）

    # 设置这个 cut section 使用绑定的摄像机
    camera_cut_section.set_camera_binding_id(camera_binding.get_id())

    unreal.log("Camera successfully bound to sequence.")


def random_hdri(hdri_backdrop):
    selected_hdri_path = select_random_asset('/HDRIBackdrop/Textures')
    hdri_texture = unreal.load_asset(selected_hdri_path)
    hdri_backdrop.set_editor_property('cubemap', hdri_texture)

def render(output_path, start_frame=0, num_frames=0, mode="rgb"):
    subsystem = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)
    pipelineQueue = subsystem.get_queue()
    # delete all jobs before rendering
    for job in pipelineQueue.get_jobs():
        pipelineQueue.delete_job(job)                                                                                                                                                           

    ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    current_world = ues.get_editor_world()
    map_name = current_world.get_path_name()

    job = pipelineQueue.allocate_new_job(unreal.MoviePipelineExecutorJob)
    job.set_editor_property('map', unreal.SoftObjectPath(map_name))
    job.set_editor_property('sequence', unreal.SoftObjectPath('/Game/RenderSequencer'))

    # This is already set (because we duplicated the main queue) but this is how you set what sequence is rendered for this job
    job.author = "Voia"
    job.job_name = "Synthetic Data"

    # Example of configuration loading
    if mode == 'rgb':
        newConfig = unreal.load_asset("/Game/MoviePipelinePrimaryConfig/RGB")
    else:
        newConfig = unreal.load_asset("/Game/MoviePipelinePrimaryConfig/CameraNormal")
    job.set_configuration(newConfig)

    # Now we can configure the job. Calling find_or_add_setting_by_class is how you add new settings or find the existing one.
    outputSetting = job.get_configuration().find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
    outputSetting.output_resolution = unreal.IntPoint(1920, 1080) # HORIZONTAL
    outputSetting.file_name_format = "Image.{render_pass}.{frame_number}"
    outputSetting.flush_disk_writes_per_shot = True  # Required for the OnIndividualShotFinishedCallback to get called.
    outputSetting.output_directory = unreal.DirectoryPath(path=f'{output_path}/{mode}')
    use_custom_playback_range = num_frames > 0
    outputSetting.use_custom_playback_range = use_custom_playback_range
    outputSetting.custom_start_frame = start_frame
    outputSetting.custom_end_frame = start_frame + num_frames

    renderPass = job.get_configuration().find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase)

    # remove default
    jpg_settings = job.get_configuration().find_setting_by_class(unreal.MoviePipelineImageSequenceOutput_JPG)
    job.get_configuration().remove_setting(jpg_settings)
    # if cs_709:
    #     set_709_color_space(job)

    png_settings = job.get_configuration().find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_PNG)
    png_settings.set_editor_property('write_alpha', False)

    # set render presets for given location
    # set_render_presets(self.rendering_stage, render_presets)

    job.get_configuration().initialize_transient_settings()

    # render...
    error_callback = unreal.OnMoviePipelineExecutorErrored()

    def movie_error(pipeline_executor, pipeline_with_error, is_fatal, error_text):
        unreal.log(pipeline_executor)
        unreal.log(pipeline_with_error)
        unreal.log(is_fatal)
        unreal.log(error_text)

    error_callback.add_callable(movie_error)

    def movie_finished(pipeline_executor, success):
        unreal.log('movie finished')
        unreal.log(pipeline_executor)
        unreal.log(success)
        # unreal.log(self.rendering_stage)

        # TODO: call render again with normals configuration
        if mode == 'rgb':
            render(output_path=output_path, mode="normals")
        # elif mode == 'normals':
        #     unreal.SystemLibrary.quit_editor()

    finished_callback = unreal.OnMoviePipelineExecutorFinished()
    finished_callback.add_callable(movie_finished)

    unreal.log("Starting Executor")
    # executor = subsystem.render_queue_with_executor(unreal.MoviePipelinePIEExecutor)
    global executor
    executor = unreal.MoviePipelinePIEExecutor(subsystem)
    # if executor:
    executor.set_editor_property('on_executor_errored_delegate', error_callback)
    executor.set_editor_property('on_executor_finished_delegate', finished_callback)

    subsystem.render_queue_with_executor_instance(executor)


if __name__ == '__main__':
    # get sequencer and clean it (keep only camera) ······· ``
    level_sequence = unreal.load_asset('/Game/RenderSequencer.RenderSequencer')
    clean_sequencer(level_sequence)

    # assumin a single camera and a single hdri
    #camera, hdri_backdrop = find_relevant_assets() 
    cameras, target_points = find_relevant_assets(level_sequence)

    # find the intersect of keys
    random_keys = [k for k in cameras.keys() if k in target_points.keys()]
    random_key = random.choice(random_keys)
    camera = cameras[random_key]
    target_point = target_points[random_key]

    look_at_target(camera, target_point)
    # # hdri
    # random_hdri(hdri_backdrop)

    #location = target_point.get_actor_location()
    # location = unreal.Vector(-990, -290, 0.0)
    bind_camera_to_sequence(level_sequence, camera)

    # character
    selected_skeletal_mesh_path = select_random_asset('/Game/ActorcoreCharacter/', asset_class='SkeletalMesh')
    actor = spawn_actor(asset_path=selected_skeletal_mesh_path, location=location)
    spawnable_actor = level_sequence.add_spawnable_from_instance(actor)

    
    # animation (Selected random animation)
    selected_animation_path = select_random_asset('/Game/ActorcoreMotion') 
    add_animation_to_actor(spawnable_actor, animation_path=selected_animation_path)

    # delete the original import (keeping only the spawnable actor)
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).destroy_actor(actor)

    # exit()

    # update camera location relative to actor
    # scene_camera_location = camera.get_editor_property('root_component').get_editor_property('relative_location')
    # scene_camera_location.set_editor_property('x', scene_camera_location.x + location.x)
    # scene_camera_location.set_editor_property('y', scene_camera_location.y + location.y)
    # scene_camera_location.set_editor_property('z', scene_camera_location.z + location.z)


    unreal.log(f"Selected character and animation: {selected_skeletal_mesh_path}, {selected_animation_path}")
   
    # this will render two passes (first is rgb following by normals)
    render(output_path=r"D:\SyntheticData\auto", mode="rgb")